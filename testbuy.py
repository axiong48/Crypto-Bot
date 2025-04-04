import ccxt
import kucoin
import datetime
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import kucoin.client
import time
import numpy as np
from backtesting import Strategy
from backtesting import Backtest
import tkinter as tk
import warnings
import mplfinance as mpf
import matplotlib.pyplot as plt
import matplotlib.backends.backend_tkagg as tkagg
# import kucoin_futures as kf
# from kucoin_futures.client import User
# from kucoin_futures.client import Trade
import requests
import hashlib
import hmac
import urllib.parse
import base64
from flask import Flask, jsonify, render_template
import threading
import get_cryptodata

# def get_eth_price():
#     open_resp = kraken_request("/0/public/Ticker?pair=ETHUSDT", {
#     "nonce": str(int(1000*time.time())),
# }, api_key, api_secret)
#     ret_json = open_resp.json()
#     ret_resp = ret_json['result']['ETHUSDT']['c'][0]
#     return ret_resp

# def buy_eth(buy_size, symb):
#     eth_price = get_eth_price()
#     vol = buy_size/eth_price
#     open_resp = kraken_request("/0/private/AddOrder", {
#     "nonce": str(int(1000*time.time())),
#     "ordertype": "market",
#     "type": "buy",
#     "volume": vol,
#     "pair": symb
#     ""
# }, api_key, api_secret)
#     ret_json = open_resp.json()
#     ret_resp = ret_json['result']['USDT']
#     return ret_resp
loop_running = False
api_key = ''
api_secret = ''
api_url = "https://api.kraken.com"
warnings.filterwarnings("ignore", category=FutureWarning)

def get_kraken_sign(urlpath, data, secret):
    postdata = urllib.parse.urlencode(data)
    encoded = (str(data['nonce']) + postdata).encode()
    message = urlpath.encode() + hashlib.sha256(encoded).digest()

    mac = hmac.new(base64.b64decode(secret), message, hashlib.sha512)
    sigdigest = base64.b64encode(mac.digest())
    return sigdigest.decode()

def kraken_request(url_path, data, api_key, api_sec):
    headers = {"API-Key": api_key, 
               "API-Sign": get_kraken_sign(url_path, data, api_sec)}
    resp = requests.post((api_url + url_path), headers = headers, data = data)
    return resp




# print((bal_result))

# amount_to_spend = base_currency_balance * 0.01

# resp = kraken_request("/0/private/AddOrder", {
#     "nonce": str(int(1000*time.time())),
#     "ordertype": "market",
#     "type": "buy",
#     "volume": 0.01,
#     "pair": "ETHUSDT"
# }, api_key, api_secret)
def get_hourly_data(api_key, api_secret, api_passphrase, sym):

    client = kucoin.client.Client(api_key, api_secret, api_passphrase)
    # client_f = kf.client(api_key, api_secret, api_passphrase)
    # Set the trading pair for Ethereum
    symbol = sym

    # Set the interval to '1hour'
    interval = '15min'

    # Set the number of candles to retrieve (maximum is 1500)
    lim = 15000

    # Retrieve the historical klines (candles) data
    end_timestamp = int(datetime.datetime.now().timestamp())
    start_timestamp = end_timestamp - (60 * 24 * 60 * 60 * 60)
    historical_data = client.get_kline_data(symbol, interval, start_timestamp, end_timestamp)

     # Extract the OHLCV values for each candlestick
    candles = []
    for candle in historical_data:
        timestamp = pd.to_datetime(int(candle[0]), unit='s', origin='unix')
        open_price = float(candle[1])
        high_price = float(candle[2])
        low_price = float(candle[3])
        close_price = float(candle[4])
        volume = float(candle[5])

        candles.append({
            'Timestamp': timestamp,
            'Open': open_price,
            'High': high_price,
            'Low': low_price,
            'Close': close_price,
            'Volume': volume
        })

    # Create a pandas DataFrame with the candlestick data
    df = pd.DataFrame(candles)
    df.set_index('Timestamp', inplace=True)
    df = df.iloc[::-1]
    # accounts = client_f.get_accounts()
    # for acc in accounts:
    #     if acc['currency'] == 'USDT':
    #         print(acc['available'])

    return df

def get_ta(crypto_df):
    crypto_df['rsi'] = ta.rsi(crypto_df['Close'])

    crypto_df['ema50'] = ta.ema(crypto_df['Close'], length = 50)
    crypto_df['ema100'] = ta.ema(crypto_df['Close'], length = 100)
    crypto_df['ema150'] = ta.ema(crypto_df['Close'], length = 150)
    crypto_df['ATR'] = crypto_df.ta.atr()
    backrollingN = 40

    crypto_df['slopeEMA50'] = crypto_df['ema50'].diff(periods = 1)
    crypto_df['slopeEMA50'] = crypto_df['slopeEMA50'].rolling(window = backrollingN).mean()

    crypto_df['slopeEMA100'] = crypto_df['ema100'].diff(periods = 1)
    crypto_df['slopeEMA100'] = crypto_df['slopeEMA100'].rolling(window = backrollingN).mean()

    crypto_df['slopeEMA150'] = crypto_df['ema150'].diff(periods = 1)
    crypto_df['slopeEMA150'] = crypto_df['slopeEMA150'].rolling(window = backrollingN).mean()

    crypto_df["VWAP"] = ta.vwap(crypto_df.High, crypto_df.Low, crypto_df.Close, crypto_df.Volume)
    
    return crypto_df


def Tot_VWAP_signal(l, df):
    close_distance = 25
    if (df.candleEMA[l]==2 and df.VWAPSignal[l]==2#and df.EngulfingSignal[l]==2 
        and min(abs(df.VWAP[l]-df.High[l]),abs(df.VWAP[l]-df.Low[l]))<=close_distance):
            return 2
    if (df.candleEMA[l]==1 and df.VWAPSignal[l]==1#and df.EngulfingSignal[l]==1 
        and min(abs(df.VWAP[l]-df.High[l]),abs(df.VWAP[l]-df.Low[l]))<=close_distance):
            return 1

def get_cond(df):
    conditions = [
        ((df['ema50'] < df['ema100']) & (df['ema100'] < df ['ema150']) & (df['slopeEMA50'] < 0) & (df['slopeEMA100'] < 0) & (df['slopeEMA150'] < 0) ),
        ((df['ema50'] > df['ema100']) & (df['ema100'] > df ['ema150']) & (df['slopeEMA50'] > 0) & (df['slopeEMA100'] > 0) & (df['slopeEMA150'] > 0) )
    ]
    choices = [1, 2]
    df['EMAsignal'] = np.select(conditions, choices, default = 0)

    TotSignal = [0] * len(df)
    for row in range(0, len(df)):
        TotSignal[row] = 0
        if df.EMAsignal[row] == 1 and df.Open[row] > df.ema50[row] and df.Close[row] < df.ema50[row]:
            TotSignal[row] = 1
        if df.EMAsignal[row] == 2 and df.Open[row] < df.ema50[row] and df.Close[row] > df.ema50[row]:
            TotSignal[row] = 2
    df['TotSignal'] = TotSignal

    candle_ema_signal = [0]*len(df)
    backcandles = 6

    for row in range(backcandles, len(df)):
        upt = 1 
        dnt = 1
        for i in range(row - backcandles, row+1):
            if df.High[i] >= df.ema100[i]:
                dnt = 0
            if df.Low[i] <= df.ema100[i]:
                upt = 0
            if upt==1 and dnt==1:
                #print("!!!!! check trend loop !!!!")
                candle_ema_signal[row]=3
            elif upt==1:
                candle_ema_signal[row]=2
            elif dnt==1:
                candle_ema_signal[row]=1
    df['candleEMA'] = candle_ema_signal

    VWAPsignal = [0]*len(df)
    backcandles = 3
    for row in range(backcandles, len(df)):
        upt = 1
        dnt = 1
        for i in range(row-backcandles, row+1):
            if df.High[i]>=df.VWAP[i]:
                dnt=0
            if df.Low[i]<=df.VWAP[i]:
                upt=0
        if upt==1 and dnt==1:
            #print("!!!!! check trend loop !!!!")
            VWAPsignal[row]=3
        elif upt==1:
            VWAPsignal[row]=2
        elif dnt==1:
            VWAPsignal[row]=1
    df['VWAPSignal'] = VWAPsignal

    Tot_VWAP = [0]*len(df)
    for row in range(0, len(df)):
        Tot_VWAP[row] = Tot_VWAP_signal(row, df)
    df["TotVWAPSignal"] = Tot_VWAP

    return df


def pointpos(x):
    if x['TotSignal'] == 1:
        return x['High']+1e-3
    elif x['TotSignal'] == 2:
        return x['Low'] -1e-3
    else:
        return np.nan

##########################################################################################################
#         HELPER FUNNCTIONS TO GET MAKE API CALLS EASIER

def get_crypto_data():
    api_key = ''
    api_secret = ''
    api_passphrase = 'laserbeam'  # Only needed for certain API endpoints
    endpoint = 'https://api.kucoin.com'


    symbol = 'ETH-USDT'  # Replace with the symbol you want to trade
#   crypto_data = get_hourly_data(api_key, api_secret, api_passphrase, symbol)
    crypto_data = get_cryptodata.get_all_data()
    crypto_data = get_ta(crypto_data)
    crypto_data = get_cond(crypto_data)
    crypto_data['pointpos'] = crypto_data.apply(lambda row: pointpos(row), axis = 1)
    return crypto_data
# def update_data():
#     crypto_df = get_hourly_data(api_key, api_secret, api_passphrase, symbol)
#     crypto_df = get_ta(crypto_df)
#     crypto_df = get_cond(crypto_df)
#     return crypto_df
def trailing_stop_loss(df, atr_multipler):
    last_price = df.Close[-1]
    last_atr = df.ATR[-1]
    stop_loss = last_price - (last_atr * atr_multipler)
    return stop_loss

def change_sl(sl, order_id, sym):
    change_response = kraken_request("/0/private/EditOrder", {     
        "nonce": str(int(1000*time.time())),
        "txid": order_id,
        "pair": sym,
        "price": sl,
    }, api_key, api_secret)
    return change_response

def get_eth_price():
    open_resp = kraken_request("/0/public/Ticker?pair=ETHUSDT", {
    "nonce": str(int(1000*time.time())),
}, api_key, api_secret)
    ret_json = open_resp.json()
    ret_resp = ret_json['result']['ETHUSDT']['c'][0]
    return ret_resp

def get_open_orders():
    open_resp = kraken_request("/0/private/OpenOrders", {
    "nonce": str(int(1000*time.time())),
}, api_key, api_secret)
    ret_json = open_resp.json()
    ret_resp = ret_json['result']['open']
    return ret_resp

def get_closed_orders():
    open_resp = kraken_request("/0/private/ClosedOrders", {
    "nonce": str(int(1000*time.time())),
}, api_key, api_secret)
    ret_json = open_resp.json()
    #ret_resp = ret_json['result']['closed']
    return ret_json

def get_balance():
    open_resp = kraken_request("/0/private/Balance", {
    "nonce": str(int(1000*time.time())),
}, api_key, api_secret)
    ret_json = open_resp.json()
    ret_resp = ret_json['result']['USDT']
    return ret_resp

def buy_eth(buy_size, symb, otype, bstype, tp):
    eth_price = get_eth_price()
    vol = buy_size/eth_price
    open_resp = kraken_request("/0/private/AddOrder", {
    "nonce": str(int(1000*time.time())),
    "ordertype": otype,
    "type": bstype,
    "volume": vol,
    "pair": symb,
    "price": tp
}, api_key, api_secret)
    ret_json = open_resp.json()
    return ret_json

#########################################
# START LOOP FUNCTION 

def loop_function():
    global loop_running
    while loop_running:
        print('Loop is running')
        time.sleep(60*5)
        df = get_crypto_data()
        has_order = get_open_orders()
        order_id = 'XXXXXX'
        order_id_sl = 'XXXXXX'
        bought_price = 0.0


        if len(has_order) >= 1:
            time.sleep(3)
            closed_buy_order = get_closed_orders()
            closed_buy_id = next(iter(closed_buy_order['result']['closed']))
            bought_price = closed_buy_order['result']['closed'][closed_buy_id]['price']
            bought_price = float(bought_price)
            print("We have an order!")
            active_orders = get_open_orders()
            order_id_sl = next(iter(active_orders))
            
            slatr = 2*df.ATR[-1]
            tpslratio = 2
            tp1 = round(df.Close[-1] + slatr*tpslratio, 2)

        if len(has_order) == 0 and df.TotVWAPSignal[-1] == 2: #IF WE HAVE NO ORDERS AND A BUY SIGNAL AT THE MOST RECENT CLOSING TIME BUY AT MARKET
            #GETTING THE ACCOUNT BALANCE AND VOLUME SO THAT WHEN WE WANT TO USE 75% OF OUR ACCOUNT WE CAN.
            acc_bal = get_balance()
            buy_size = float(acc_bal)*0.75
            eth_price = float(get_eth_price())
            buy_vol = buy_size/eth_price
            buy_response = kraken_request("/0/private/AddOrder", {     
                "nonce": str(int(1000*time.time())),
                "ordertype": "market",
                "type": "buy",
                "volume": 0.01,
                "pair": "ETHUSDT",
            }, api_key, api_secret)
            buy_result = buy_response.json()

            order_id_buy = buy_result['result']['txid'][0]
            closed_buy_order = get_closed_orders()
            bought_price = closed_buy_order['result']['closed'][order_id_buy]['price']

            time.sleep(2)

            print("bought at: ", bought_price)
            print("Time: ", datetime.datetime.now())

            df = get_crypto_data()
            slatr = 2*df.ATR[-1]
            tpslratio = 2
            sl1 = round(df.Close[-1] - slatr, 2)
            tp1 = round(df.Close[-1] + slatr*tpslratio, 2)

            sl_response = kraken_request("/0/private/AddOrder", {   #PUT STOP LOSS AT ATR
                "nonce": str(int(1000*time.time())),
                "ordertype": "stop-loss",
                "type": "sell",
                "volume": 0.01,
                "pair": "ETHUSDT",
                "price": sl1,
            }, api_key, api_secret)
            sl_json = sl_response.json()
            time.sleep(2)
            order_id_sl = sl_json['result']['txid'][0]
            time.sleep(1)
            print("Here is the Stop Loss: ", sl1)

            # price_bought = orders_json['result']['']
        # HOW DO WE CHECK IF IT'S READY TO BE SOLD? TAKE PROFIT? 
        #IF PRICE IS ABOVE OR AT TAKE PROFIT THEN SELL? NEEDS TO HAVE ORDER AS WELL? WHAT'S THE POINT OF THE TOTSIGNAL THEN? 
        #REAL QUESTION IS, DOES THE TOTSIGNAL ALWAYS MEET THE TAKE PROFIT PRICE? OR SHOULD WE JUST SELL FOR MARKET VALUE WHEN WE GET THE SELL SIGNAL??
        curr_eth_price = float(get_eth_price())
        
        if len(has_order) >= 1 and (curr_eth_price > bought_price): #MAY NEED TO CHANGE IT SO THAT WE COMPARE THE CURRENT ETH PRICE AND THE PRICE THAT WE BOUGHT IT AT
            new_sl_df = get_crypto_data()
            new_slatr = 2*new_sl_df.ATR[-1]
            new_sl1 = round(new_sl_df.Close[-1] - new_slatr, 2)
            time.sleep(5)
            print("here is the new stop loss: ", new_sl1)
            sl_order = get_open_orders()
            order_id_sl = next(iter(sl_order))
            new_sl_response = change_sl(new_sl1, order_id_sl, 'ETHUSDT')
            print("Here's the order id: ", order_id_sl)
            print("Changed Stop Loss: ", new_sl_response.json())
            time.sleep(2)

        if len(has_order) >= 1 and (df.TotVWAPSignal[-1] == 1 or curr_eth_price >= tp1) : #greater than TAKE PROFIT HERE
            cancel_response = kraken_request("/0/private/CancelAll", {     
                "nonce": str(int(1000*time.time())),
            }, api_key, api_secret)
            cancel_json = cancel_response.json()
            print("canceled all orders: ", cancel_json)
            time.sleep(2)

            selltp_response = kraken_request("/0/private/AddOrder", {   
                "nonce": str(int(1000*time.time())),
                "ordertype": "market",
                "type": "sell",
                "volume": 0.01,
                "pair": "ETHUSDT",
            }, api_key, api_secret)
            selltp_json = selltp_response.json()
            print("sell response: ", selltp_json)
            print("sold at: ", curr_eth_price)
            print("Time: ", datetime.datetime.now())







app = Flask(__name__)
@app.route('/')
def index():
    return render_template('index.html', data = show_dataframe())

@app.route('/invest', methods = ['POST'])
def invest():
    global loop_running, loop_thread
    if not loop_running:
        loop_running = True
        loop_thread = threading.Thread(target=loop_function)
        loop_thread.start()
        return jsonify({'message': 'Loop started'})
    else:
        return jsonify({'message': 'Loop is already running'})
    return 

@app.route('/stop-invest', methods = ['POST'])
def stop_invest():
    global loop_running
    loop_running = False
    return jsonify({'message': 'Loop stopped'})

    

@app.route('/show_dataframe')
def show_dataframe():
    api_key = ''
    api_secret = ''
    api_passphrase = 'laserbeam'  # Only needed for certain API endpoints
    endpoint = 'https://api.kucoin.com'


    symbol = 'ETH-USDT'  # Replace with the symbol you want to trade
    #crypto_data = get_hourly_data(api_key, api_secret, api_passphrase, symbol)
    crypto_data = get_cryptodata.get_all_data()
    crypto_data = get_ta(crypto_data)
    crypto_data = get_cond(crypto_data)
    crypto_data['pointpos'] = crypto_data.apply(lambda row: pointpos(row), axis = 1)
    json_df = crypto_data.tail(5).to_json(orient='records')
    return json_df

if __name__ == '__main__':
    api_key = ''
    api_secret = ''
    api_url = "https://api.kraken.com"
    app.run(debug=True)

