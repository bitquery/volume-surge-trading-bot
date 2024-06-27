import requests
from datetime import datetime, timedelta, timezone
from web3 import Web3
import time
import os

# Configuration
BITQUERY_AUTH_TOKEN = "ory_at_.."
TOKEN_ADDRESS = '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2'  # Address of the token to track
INFURA_URL = 'https://eth-sepolia.g.alchemy.com/v2/YTg4XGDZmgtjMXggnHyrKLzeLUhQ4eiO'  # Sepolia testnet URL
PRIVATE_KEY = 'e...'  # Private key for transactions
ADDRESS = '0xF4a86386e0297E1D53Ece30541091dda8098Ead5'  # Address from which transactions will originate
VOLUME_SURGE_THRESHOLD = 0.1  # Threshold for volume surge detection (0.1% increase)
TIME_WINDOW_MINUTES = 60  # Time window in minutes for historical data fetching

# Predefined time range for historical data query
PREDEFINED_SINCE_DATE = (datetime.now(timezone.utc) - timedelta(minutes=TIME_WINDOW_MINUTES)).strftime("%Y-%m-%dT%H:%M:%SZ")
PREDEFINED_TILL_DATE = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
print(f"PREDEFINED_SINCE_DATE: {PREDEFINED_SINCE_DATE}")
print(f"PREDEFINED_TILL_DATE: {PREDEFINED_TILL_DATE}")

# Function to fetch historical volume data from Bitquery
def fetch_volume_data(token_address):
    print("Fetching volume data...")
    query = """
    {
      EVM(dataset: realtime, network: eth) {
        DEXTradeByTokens(
          where: {Trade: {Currency: {SmartContract: {is: "%s"}}}, Block: {Time: {since: "%s", till: "%s"}}}
        ) {
          buy: sum(of: Trade_AmountInUSD)
          sell: sum(of: Trade_Side_AmountInUSD)
          count
        }
      }
    }
    """ % (token_address, PREDEFINED_SINCE_DATE, PREDEFINED_TILL_DATE)

    print("Querying Bitquery API...")
    try:
        response = requests.post(
            'https://streaming.bitquery.io/graphql',
            json={'query': query},
            headers={'Authorization': f'Bearer {BITQUERY_AUTH_TOKEN}'}
        )

        if response.status_code == 200:
            print("Data successfully fetched.")
            data = response.json()
            trades = data['data']['EVM']['DEXTradeByTokens']
            if not trades:
                print("No trades found.")
            else:
                print("Fetched trades:")
                for trade in trades:
                    print(f" Buy Volume: {trade['buy']} USD, Sell Volume: {trade['sell']} USD")
            return trades
        else:
            raise Exception(f"Failed to fetch data: {response.text}")

    except Exception as e:
        print(f"Error in fetch_volume_data: {str(e)}")
        return None

# Function to calculate total volume traded for the token
def get_volume():
    try:
        print("Calculating token volume...")
        trades = fetch_volume_data(TOKEN_ADDRESS)
        if trades is None:
            return 0  # No trades, so volume is 0

        total_volume = sum(float(trade['buy']) + float(trade['sell']) for trade in trades)
        print(f"Total volume: {total_volume}")
        return total_volume
    except Exception as e:
        print(f"Error in get_volume: {str(e)}")
        return 0  # Return 0 volume on error

# Function to check if there is a volume surge
def check_volume_surge(initial_volume, current_volume):
    print("Checking volume surge condition...")
    if initial_volume > 0:
        increase_percentage = ((current_volume - initial_volume) / initial_volume) * 100
        print(f"For Time: {PREDEFINED_SINCE_DATE}" + " the " + f"increase percentage is: {increase_percentage}%")
        return True
    return False

# Function to execute a buy order on the testnet
def execute_buy_order(token_address):
    try:
        print("Executing buy order...")
        web3 = Web3(Web3.HTTPProvider(INFURA_URL))
        nonce = web3.eth.get_transaction_count(ADDRESS)
        value = Web3.to_wei(0.1, 'ether')
        gas_price = Web3.to_wei('50', 'gwei')  # Convert 50 Gwei to Wei
        
        transaction = {
            'nonce': nonce,
            'to': ADDRESS,
            'value': value,
            'gas': 2000000,
            'gasPrice': gas_price
        }
        
        signed_tx = web3.eth.account.sign_transaction(transaction, PRIVATE_KEY)
        tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
        print(f"Transaction sent. Hash: {web3.toHex(tx_hash)}")
        return web3.toHex(tx_hash)
    except Exception as e:
        print(f"Error in execute_buy_order: {str(e)}")
        return None

# Main function to run the bot
def main():
    try:
        initial_volume = get_volume()
        print("Initial Volume:", initial_volume)

        while True:
            current_volume = get_volume()
            print("Current Volume:", current_volume)

            if check_volume_surge(initial_volume, current_volume):
                print(f"Volume surge detected. Executing buy order.")
                tx_hash = execute_buy_order(TOKEN_ADDRESS)
                if tx_hash:
                    print(f"Transaction hash: {tx_hash}")

            time.sleep(60 * 1)  # Check every 1 minute

    except Exception as e:
        print(f"Error occurred: {str(e)}")

if __name__ == "__main__":
    main()
