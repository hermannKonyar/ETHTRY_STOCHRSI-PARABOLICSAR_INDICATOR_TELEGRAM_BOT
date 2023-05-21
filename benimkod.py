import pandas as pd
import requests
import talib
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext, JobQueue


class Data:
    def __init__(self,interval,symbol,period):
        self.interval = interval
        self.symbol = symbol
        self.period = period
        self.k = None
        self.d = None

    def fetchData(self):
        binanceUrl='https://api.binance.com/api/v3/klines'
        params = {
            'symbol': self.symbol.upper(),
            'interval': self.interval
        }
        reponse = requests.get(binanceUrl,params=params)
        data = reponse.json()

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

        self.k = stoch_rsi_k.iloc[-1]
        self.d = stoch_rsi_d.iloc[-1]

        self.analyze_data()

    def analyze_data(self):
        if self.k is not None and self.d is not None:
            if self.k > 70 and self.d > 70:
                action = 'SAT'
            elif self.k < 30 and self.d < 30:
                action = 'AL'
            else:
                action = None
            return action


class Telegram:
    def __init__(self,TOKEN,CHAT_ID, data_obj):
        self.token=TOKEN
        self.chat_id=CHAT_ID
        self.data_obj = data_obj
        self.runBot()

    def runBot(self):
        updater=Updater(token=self.token)
        dispatcher=updater.dispatcher
        dispatcher.add_handler(CommandHandler('start',self.basla))
        updater.start_polling()

        job_queue = updater.job_queue
        job_queue.run_repeating(self.callback_function, interval=60, first=0)

        updater.idle()

    def basla(self,update:Update,_:CallbackContext):
        update.message.reply_text('Ben bir telegram botuyum')

    def callback_function(self, context: CallbackContext):
        action = self.data_obj.fetchData()
        if action is not None:
            context.bot.send_message(chat_id=self.chat_id,
                                     text=f'Son Stokastik RSI K değeri: {self.data_obj.k:.2f}, D değeri: {self.data_obj.d:.2f}, Yapılacak işlem: {action}')


if __name__=='__main__':
    data_obj = Data('15m','ethtry',14)
    Telegram('6247116301:AAFShT7Nk9yn-Hm5AfbPYPAO7EMDBV5TYOY','804636818', data_obj)
