from trade_client import *
from store_order import *
from load_config import *
from new_listings_scraper import *

from collections import defaultdict
from datetime import datetime, time
import time
import threading

import json
import os.path


# loads local configuration
config = load_config('config.yml')

# load necesarry files
if os.path.isfile('sold.json'):
    sold_coins = load_order('sold.json')
else:
    sold_coins = {}

if os.path.isfile('order.json'):
    order_made = load_order('order.json')
else:
    order_made = {}

if os.path.isfile('new_listing.json'):
    announcement_coin = load_order('new_listing.json')
else:
    announcement_coin = False


def main():
    """
    Sells, adjusts TP and SL according to trailing values
    and buys new coins
    """
    # store config deets
    tp = config['TRADE_OPTIONS']['TP']
    sl = config['TRADE_OPTIONS']['SL']
    enable_tsl = config['TRADE_OPTIONS']['ENABLE_TSL']
    tsl = config['TRADE_OPTIONS']['TSL']
    ttp = config['TRADE_OPTIONS']['TTP']
    pairing = config['TRADE_OPTIONS']['PAIRING']
    qty = config['TRADE_OPTIONS']['QUANTITY']
    frequency = config['TRADE_OPTIONS']['RUN_EVERY']
    test_mode = config['TRADE_OPTIONS']['TEST']

    t = threading.Thread(target=search_and_update)
    t.start()


    while True:
        #try:

            # check if the order file exists and load the current orders
            # basically the sell block and update TP and SL logic
            if len(order_made) > 0:

                for coin in list(order_made):

                    # store some necesarry trade info for a sell
                    stored_price = float(order_made[coin]['price'])
                    coin_tp = order_made[coin]['tp']
                    coin_sl = order_made[coin]['sl']
                    volume = order_made[coin]['volume']
                    symbol = order_made[coin]['symbol']

                    last_price = get_last_price(symbol, pairing)
                    print("last_price: {}, stored_price: {}".format(last_price, stored_price))
                    # update stop loss and take profit values if threshold is reached
                    if float(last_price) > stored_price and enable_tsl:

                        # same deal as above, only applied to trailing SL
                        new_sl = float(last_price) - (float(last_price) * (float(tsl)/100))

                        # new values to be added to the json file
                        order_made[coin]['price'] = last_price
                        order_made[coin]['sl'] = new_sl
                        store_order('order.json', order_made)
                        print("new_sl: {}".format(new_sl))


                    # close trade if tsl is reached or trail option is not enabled
                    elif float(last_price) < stored_price - (stored_price*sl /100) or float(last_price) > stored_price + (stored_price*coin_tp /100) and not enable_tsl:
                        try:
                            # sell for real if test mode is set to false
                            if not test_mode:
                                print("TRYING TO SELL for usdt:{}".format((float(volume)*(99.5/100)) * float(last_price)))
                                sell = place_order(symbol, pairing, (float(volume)*(99.5/100)) * float(last_price), 'sell', last_price)

                            print(f"[BUY-Thread]sold {coin} with {(float(last_price) - stored_price) / float(stored_price)*100}% PNL")

                            # remove order from json file
                            order_made.pop(coin)
                            store_order('order.json', order_made)

                        except Exception as e:
                            print(e)

                        # store sold trades data
                        else:
                            if not test_mode:
                                sold_coins[coin] = {
                                            'symbol':coin,
                                            'price':sell.price,
                                            'volume':sell.amount,
                                            'time':datetime.timestamp(datetime.now()),
                                            'tp': tp,
                                            'sl': sl,
                                            'id': sell.id,
                                            'text': sell.text,
                                            'create_time': sell.create_time,
                                            'update_time': sell.update_time,
                                            'currency_pair': sell.currency_pair,
                                            'status': sell.status,
                                            'type': sell.type,
                                            'account': sell.account,
                                            'side': sell.side,
                                            'iceberg': sell.iceberg
                                }
                                store_order('sold.json', sold_coins)
                            else:
                                sold_coins[coin] = {
                                            'symbol':coin,
                                            'price':last_price,
                                            'volume':volume,
                                            'time':datetime.timestamp(datetime.now()),
                                            'profit': float(last_price) - stored_price,
                                            'relative_profit_%': round((float(last_price) - stored_price) / stored_price*100, 3),
                                            'id': 'test-order',
                                            'text': 'test-order',
                                            'create_time': datetime.timestamp(datetime.now()),
                                            'update_time': datetime.timestamp(datetime.now()),
                                            'currency_pair': f'{symbol}_{pairing}',
                                            'status': 'closed',
                                            'type': 'limit',
                                            'account': 'spot',
                                            'side': 'sell',
                                            'iceberg': '0',
                                            'price': last_price}

                                store_order('sold.json', sold_coins)


            # the buy block and logic pass
            #announcement_coin = load_order('new_listing.json')
            if os.path.isfile('new_listing.json'):
                announcement_coin = load_order('new_listing.json')
            else:
                announcement_coin = False

            if announcement_coin and announcement_coin not in order_made and announcement_coin not in sold_coins:
                print(f'[BUY-Thread]New announcement detected: {announcement_coin}')
                price = get_last_price(announcement_coin, pairing)
                try:
                    # Run a test trade if true
                    if config['TRADE_OPTIONS']['TEST']:
                        order_made[announcement_coin] = {
                                    'symbol':announcement_coin,
                                    'price':price,
                                    'volume':qty,
                                    'time':datetime.timestamp(datetime.now()),
                                    'tp': tp,
                                    'sl': sl,
                                    'id': 'test-order',
                                    'text': 'test-order',
                                    'create_time': datetime.timestamp(datetime.now()),
                                    'update_time': datetime.timestamp(datetime.now()),
                                    'currency_pair': f'{announcement_coin}_{pairing}',
                                    'status': 'filled',
                                    'type': 'limit',
                                    'account': 'spot',
                                    'side': 'buy',
                                    'iceberg': '0'
                                    }
                        print('[BUY-Thread]PLACING TEST ORDER')
                    # place a live order if False
                    else:
                        print("[BUY-Thread]placing order")
                        order_made[announcement_coin] = {}
                        ORDER = place_order(announcement_coin, pairing, qty,'buy', float(price)* 1.1)
                        order_made[announcement_coin] =order_made[announcement_coin] = {
                                    'symbol':announcement_coin,
                                    'price':ORDER.price,
                                    'volume':ORDER.amount,
                                    'time':datetime.timestamp(datetime.now()),
                                    'tp': tp,
                                    'sl': float(ORDER.price) - (float(ORDER.price) * (float(tsl)/100)),
                                    'id': ORDER.id,
                                    'text': ORDER.text,
                                    'create_time': ORDER.create_time,
                                    'update_time': ORDER.update_time,
                                    'currency_pair': ORDER.currency_pair,
                                    'status': ORDER.status,
                                    'type': ORDER.type,
                                    'account': ORDER.account,
                                    'side': ORDER.side,
                                    'iceberg': ORDER.iceberg
                                    }

                except Exception as e:
                    print(e)

                else:
                    print(f"[BUY-Thread]Order created with {qty} on {announcement_coin}")

                    store_order('order.json', order_made)
            else:
                print("[BUY-Thread][{}]No coins announced, or coin has already been bought/sold. Checking more frequently in case TP and SL need updating. You can comment me out, I live on line 176 in main.py".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

            time.sleep(3)
        #except Exception as e:
            #print(e)



if __name__ == '__main__':
    print('working...')
    main()
