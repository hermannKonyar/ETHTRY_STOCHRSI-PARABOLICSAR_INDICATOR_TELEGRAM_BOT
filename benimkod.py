import pandas as pd
import requests
import talib
import numpy as np
from binance.client import Client
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext


class Data:
    def __init__(self, interval, symbol, period, telegram):
        self.interval = interval
        self.symbol = symbol
        self.period = period
        self.x = telegram

    def fetchData(self, context: CallbackContext):
        binanceUrl = 'https://api.binance.com/api/v3/klines'
        params = {
            'symbol': self.symbol.upper(),
            'interval': self.interval
        }
        response = requests.get(binanceUrl, params=params)
        data = response.json()

        df = pd.DataFrame(data)
        df.columns = ['open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_asset_volume',
                      'number_of_trades', 'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore']
        df['close'] = pd.to_numeric(df['close'])

        # Calculate RSI
        rsi = talib.RSI(df['close'], timeperiod=self.period)

        # Calculate StochRSI 'K' and 'D' lines
        stoch_rsi_k = (rsi - rsi.rolling(window=self.period).min()) / (
                rsi.rolling(window=self.period).max() - rsi.rolling(window=self.period).min())
        stoch_rsi_k = stoch_rsi_k * 100
        stoch_rsi_d = stoch_rsi_k.rolling(window=3).mean()

        context.bot_data['k'] = stoch_rsi_k.iloc[-1]
        context.bot_data['d'] = stoch_rsi_d.iloc[-1]

        self.analyze_data(context)

    def analyze_data(self, context: CallbackContext):
        k = context.bot_data.get('k')
        d = context.bot_data.get('d')

        if k is not None and d is not None:
            if k > 70 and d > 70:
                action = 'SAT'
            elif k < 30 and d < 30:
                action = 'AL'
            else:
                action = 'BEKLE'

            context.bot.send_message(chat_id=self.x.chat_id,
                                     text=f'Son Stokastik RSI K değeri: {k:.2f}, D değeri: {d:.2f}, Yapılacak işlem: {action}')


class Telegram:
    def __init__(self, TOKEN, CHAT_ID):
        self.token = TOKEN
        self.chat_id = CHAT_ID

    def runBot(self, token, data_instance):
        updater = Updater(token=self.token)
        dispatcher = updater.dispatcher
        dispatcher.add_handler(CommandHandler('start', self.basla))
        updater.start_polling()
        job_queue = updater.job_queue
        job_queue.run_repeating(data_instance.fetchData, interval=60, first=0)
        updater.idle()

    def basla(self, update: Update, _: CallbackContext):
        update.message.reply_text('Ben bir telegram botuyum')


if __name__ == '__main__':
    telegram_instance = Telegram('6247116301:AAFShT7Nk9yn-Hm5AfbPYPAO7EMDBV5TYOY', '804636818')
    data_instance = Data('15m', 'ethtry', 14, telegram_instance)
    telegram_instance.runBot('6247116301:AAFShT7Nk9yn-Hm5AfbPYPAO7EMDBV5TYOY', data_instance)
