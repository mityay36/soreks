import asyncio
import logging
import os

from requests import Session
from requests.exceptions import ConnectionError, Timeout, TooManyRedirects
from telegram import Update, Bot
from telegram.ext import Updater, CommandHandler, CallbackContext
import json
from dotenv import load_dotenv

load_dotenv()


TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
COINCAP_API_TOKEN = os.getenv('COINCAP_API_TOKEN')

user_data = {}


def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(
        'Привет! Я криптовалютный бот. '
        'Введите команду {/set <символ> '
        '<минимальная цена> <максимальная цена>} для '
        'установки оповещения.'
    )


def get_api_ans(symbol):

    url = f'https://pro-api.coinmarketcap.com/v2/cryptocurrency/quotes/latest?symbol={symbol}'
    headers = {
        'Accepts': 'application/json',
        'X-CMC_PRO_API_KEY': f'{COINCAP_API_TOKEN}',
    }

    session = Session()
    session.headers.update(headers)

    try:
        response = session.get(url)
        data = json.loads(response.text).get('data').get(symbol)[0]
        price = round(data.get('quote').get('USD').get('price'), 2)
        return price
    except (ConnectionError, Timeout, TooManyRedirects) as e:
        logging.error(e)


def set_alert(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id
    try:
        symbol = context.args[0].upper()
        min_price = float(context.args[1])
        try:
            max_price = float(context.args[2])
        except Exception as e:
            logging.error(e)
            max_price = None
        user_data[chat_id] = {'symbol': symbol, 'min_price': min_price, 'max_price': max_price}
        if max_price:
            update.message.reply_text(f'Оповещение установлено для {symbol} с минимальной '
                                      f'ценой {min_price} USD и максимальной ценой {max_price} USD.')
        else:
            update.message.reply_text(f'Оповещение установлено для {symbol} с минимальной '
                                      f'ценой {min_price} USD.')
    except (IndexError, ValueError):
        update.message.reply_text('Использование: /set <символ> <минимальная цена> <максимальная цена>')


async def check_price(bot):
    while True:
        for chat_id, data in user_data.items():
            if data is not None:
                symbol = data['symbol']
                min_price = data['min_price']
                current_price = get_api_ans(symbol)
                if current_price >= min_price:
                    bot.send_message(chat_id, text=f'Цена {symbol} достигла {current_price} USD!')
                    user_data[chat_id] = None

        await asyncio.sleep(20)


def main():
    bot = Bot(token=TELEGRAM_TOKEN)
    updater = Updater(token=TELEGRAM_TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("set", set_alert))

    updater.start_polling()

    asyncio.run(check_price(bot))

    updater.idle()


if __name__ == '__main__':
    logging.basicConfig(
        format='%(asctime)s [%(levelname)s] %(message)s',
        level=logging.INFO,
        filename='main.log',
    )
    print('Scheduler started.')
    main()
