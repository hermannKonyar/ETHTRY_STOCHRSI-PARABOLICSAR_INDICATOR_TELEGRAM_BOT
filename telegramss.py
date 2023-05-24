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
        delta = df['close'].diff()
        up = delta.clip(lower=0)
        down = -1 * delta.clip(upper=0)
        ema_up = up.ewm(com=self.period - 1, adjust=False).mean()
        ema_down = down.ewm(com=self.period - 1, adjust=False).mean()
        rs = ema_up / ema_down
        rsi = 100 - (100 / (1 + rs))

        # Calculate StochRSI 'K' and 'D' lines
        min_rsi = rsi.rolling(window=self.period).min()
        max_rsi = rsi.rolling(window=self.period).max()
        stoch_rsi = 100 * (rsi - min_rsi) / (max_rsi - min_rsi)
        stoch_rsi_k = stoch_rsi.rolling(window=3).mean()
        stoch_rsi_d = stoch_rsi_k.rolling(window=3).mean()

        # Calculate Parabolic SAR
        high = df['high'].astype(float)
        low = df['low'].astype(float)
        close = df['close'].astype(float)
        sar = talib.SAR(high, low, acceleration=0.02, maximum=0.2)

        context.bot_data['k'] = stoch_rsi_k.iloc[-1]
        context.bot_data['d'] = stoch_rsi_d.iloc[-1]
        context.bot_data['sar'] = sar.iloc[-1]
        context.bot_data['close'] = close.iloc[-1]

        self.analyze_data(context)

    def analyze_data(self, context: CallbackContext):
        k = context.bot_data.get('k')
        d = context.bot_data.get('d')
        sar = context.bot_data.get('sar')
        close = context.bot_data.get('close')

        if k is not None and d is not None and sar is not None and close is not None:
            if k<10 and d<10:
                stoch_signal = 'AL'
            elif k>90 and d>90:
                stoch_signal='SAT'
            else:
                stoch_signal='BEKLE'
            sar_signal = 'AL' if close > sar else 'SAT'

            context.bot.send_message(chat_id=self.x.chat_id,
                                     text=f'Son Stokastik RSI K değeri: {k:.2f}, D değeri: {d:.2f}, '
                                          f'Stochastic Signal: {stoch_signal}\n'
                                          f'Parabolic SAR değeri: {sar:.2f}, '
                                          f'SAR Signal: {sar_signal}')


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
    telegram_instance = Telegram()
    data_instance = Data('15m', 'ethtry', 14, telegram_instance)
    telegram_instance.runBot(, data_instance)
