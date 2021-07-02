import websocket, json, pprint, talib, numpy, os, time
from datetime import datetime
import config
from binance.client import Client
from binance.enums import *


clear = lambda: os.system('cls')

# Create web socket to listen to a specific symbol at a determined interval (<symbol>@kline_<interval>).
# https://github.com/binance/binance-spot-api-docs/blob/master/web-socket-streams.md
TIME_PERIOD = '1m'

SOCKET = f'wss://stream.binance.com:9443/ws/ethusdt@kline_{TIME_PERIOD}'

RSI_PERIOD = 30
RSI_OVERBOUGHT = 80
RSI_OVERSOLD = 20

TRADE_SYMBOL = 'ETHUSDT'
TRADE_QUANTITY = 0.005

prices = []
closes = []
status = ''
in_position = False
last_order = None
current_rsi = 0

client = Client(config.API_KEY, config.API_SECRET)
account = client.get_account()

# Gets wallet balance of owned coins.
def get_bal(coin):
    balance = account['balances']
    for i in balance:
        if i['asset'] == coin:
            return i['free'] + ' ' + coin


def order(side, quantity, symbol, order_type=ORDER_TYPE_MARKET):
    global last_order
    try:
        order = client.create_order(side=side, quantity=quantity, symbol=symbol, type=order_type)
        last_order = order
    except Exception as e:
        print(e)
        return False

    return True


# Define functions for connections and message.
def on_open(ws):
    global status
    status = 'CONNECTED TO BINANCE WEBSTREAM'

    
def on_close(ws):
    global status
    status = 'DISCONNECTED'


def on_message(ws, message):
    global closes, in_position, status, last_order, current_rsi, position

    json_message = json.loads(message)
    price = json_message['k']['c']

    # Appends closing prices and deletes those that are not used.
    closes.append(float(price))
    if len(closes) > RSI_PERIOD+1:
        del closes[0]
    prices.append(float(price))
    if len(prices) > RSI_PERIOD+1:
        del prices[0]

    rounded_price = round(float(price), 2)

    # Console.
    clear()
    print(status)
    print('-'*30)
    print('WALLET')
    print((get_bal('ETH')))
    print((get_bal('USDT')))
    print('-'*30)
    print(f'{TRADE_SYMBOL} - {str(rounded_price)}$')
    print(f'CURRENT RSI - {round(current_rsi, 2)}')
    print(f'IN POSITION: {in_position}')

    if last_order is not None:
        print(f"LAST ORDER:\n[{last_order['side']} {last_order['fills'][0]['qty']} {last_order['fills'][0]['price']}]")
        print(datetime.fromtimestamp(last_order['transactTime']/1000))
    else:
        print(f'LAST ORDER: {last_order}')

    print('-'*30)

    # Calculate RSI to execute orders.
    if len(closes) > RSI_PERIOD:
        np_closes = numpy.array(closes)
        rsi = talib.RSI(np_closes, RSI_PERIOD)
        current_rsi = rsi[-1]

        if current_rsi > RSI_OVERBOUGHT:
            if in_position:
                order_success = order(SIDE_SELL, TRADE_QUANTITY, TRADE_SYMBOL)
                if order_success:
                    in_position = False
            else:
                print('>>> UNABLE TO SELL (NOT IN POSITION)')

        if current_rsi < RSI_OVERSOLD:
            if not in_position:
                order_success = order(SIDE_BUY, TRADE_QUANTITY, TRADE_SYMBOL)
                if order_success:
                    in_position = True
            else:
                print('>>> UNABLE TO BUY (ALREADY IN POSITION)')

                
ws = websocket.WebSocketApp(SOCKET, on_open=on_open, on_close=on_close, on_message=on_message)
ws.run_forever()
