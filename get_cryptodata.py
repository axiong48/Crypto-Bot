import ccxt
import datetime
import requests
import pandas as pd
import time

api_url = "https://api.kraken.com/0/public/Ticker"


def fetch_ohlc_data(pair, interval='15', since=None, timeout=30):
    url = f"https://api.kraken.com/0/public/OHLC"
    
    params = {
        'pair': pair,
        'interval': interval,
        'since': since
    }
    
    try:
        response = requests.get(url, params=params, timeout=timeout)
        response.raise_for_status()  # Raise an exception for HTTP errors
        data = response.json()
        
        if 'result' in data and pair in data['result']:
            ohlc_data = data['result'][pair]
            return ohlc_data
        else:
            print("Error fetching OHLC data.")
            return []
    except requests.exceptions.Timeout:
        print("Request timed out while fetching OHLC data.")
        return []
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while fetching OHLC data: {e}")
        return []

def process_ohlc_data(ohlc_data):
    processed_data = []
    for entry in ohlc_data:
        timestamp, open_price, high_price, low_price, closing_price, volume, timestamp_ms, count = entry
        processed_data.append({
            'Timestamp': pd.to_datetime(timestamp, unit='s'),
            'Open': float(open_price),
            'High': float(high_price),
            'Low': float(low_price),
            'Close': float(closing_price),
            'Volume': float(volume),
        })
    df = pd.DataFrame(processed_data)
    df.set_index('Timestamp', inplace=True)
    return df

def get_all_data():
    crypto_pair = "ETHUSDT"
    current_timestamp = int(time.time())
    fifteen_days_in_seconds = 15 * 24 * 60 * 60  # 15 days in seconds
    since_timestamp = current_timestamp - fifteen_days_in_seconds
    ohlc_data = fetch_ohlc_data(crypto_pair, interval='15', since=since_timestamp)
        
    if ohlc_data:
        df = process_ohlc_data(ohlc_data)
    return df

# df = get_all_data()
# print(df)