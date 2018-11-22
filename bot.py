import base64
import logging
from pathlib import Path

import telepot
from flask import Flask, request
from telepot.loop import OrderedWebhook

import utils
from downloader import Mp3Downloader

config_path = Path('config.json')

c_channel_id = "channel_id"
c_telegram_api_key = "telegram_api_key"
c_webhook_url = "webhook_url"
c_webhook_port = "webhook_port"

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

config = utils.load_json(config_path, {})


def on_chat_message(msg):
    content_type, chat_type, chat_id = telepot.glance(msg)

    if content_type == 'text':
        text = msg['text']

        if text.startswith('/get'):
            try:
                link = text[len('/get_'):]
                link = link + '=' * (len(link) % 4)
                link = base64.b64decode(link.encode('utf-8')).decode()

                print(f'get {link}')

                mdl = Mp3Downloader()
                dl_path = mdl.download_radio_javan(link)

                bot.sendAudio(chat_id, open(dl_path, 'rb'))

            except ValueError:
                print('No payload, or more than one chunk of payload')

            except KeyError:
                print('Invalid key, no corresponding User ID')
        elif text.startswith('/search'):
            try:
                query = text[len('/search_'):]

                print(f'search {query}')

                mdl = Mp3Downloader()
                results = mdl.search_rj(query)

                if not results:
                    bot.sendMessage(chat_id, 'nothing found ☹️')
                    return

                msg = ''
                for name, link in results[:min(len(results), 10)]:
                    link = base64.b64encode(link.encode('utf-8')).decode('utf-8').replace('=', '')
                    msg += f'{name}: /get_{link}\n'

                bot.sendMessage(chat_id, msg)

            except ValueError as e:
                print('No payload, or more than one chunk of payload')


def on_callback_query(msg):
    query_id, from_id, data = telepot.glance(msg, flavor='callback_query')
    print('Callback query:', query_id, from_id, data)


# need `/setinline`
def on_inline_query(msg):
    query_id, from_id, query_string = telepot.glance(msg, flavor='inline_query')
    print('Inline Query:', query_id, from_id, query_string)

    # Compose your own answers
    articles = [{'type': 'article',
                    'id': 'abc', 'title': 'ABC', 'message_text': 'Good morning'}]

    bot.answerInlineQuery(query_id, articles)


# need `/setinlinefeedback`
def on_chosen_inline_result(msg):
    result_id, from_id, query_string = telepot.glance(msg, flavor='chosen_inline_result')
    print('Chosen Inline Result:', result_id, from_id, query_string)


TOKEN = config[c_telegram_api_key]
PORT = config[c_webhook_port]
URL = f'{config[c_webhook_url]}/{TOKEN}'

app = Flask(__name__)
bot = telepot.Bot(TOKEN)
webhook = OrderedWebhook(bot, {'chat': on_chat_message,
                               'callback_query': on_callback_query,
                               'inline_query': on_inline_query,
                               'chosen_inline_result': on_chosen_inline_result})


@app.route(f'/webhook/{TOKEN}', methods=['GET', 'POST'])
def pass_update():
    webhook.feed(request.data)
    return 'OK'


try:
    bot.setWebhook(URL)
# Sometimes it would raise this error, but webhook still set successfully.
except telepot.exception.TooManyRequestsError:
    pass

webhook.run_as_thread()
