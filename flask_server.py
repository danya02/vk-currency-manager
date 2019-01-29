import traceback

import vk_api
from flask import Flask, request

app = Flask(__name__)

with open('token.txt') as o:
    token = o.read().strip()


@app.route('/endpoint', methods=['POST'])
def main():
    data = request.get_json()
    if data['type'] == 'confirmation':
        return 'caf10767'
    if data['type'] != 'message_new':
        return 'wrong type', 401
    obj = data['object']
    text = obj['text']
    to = obj['peer_id']
    user = obj['from_id']
    try:
        msg = process_msg(text, user, to)
    except:
        msg = 'Sorry, an exception occurred while processing your request.\n'+traceback.format_exc()
    session = vk_api.VkApi(token=token)
    api = session.get_api()
    api.messages.send(peer_id=to, message=msg, random_id=0)


def process_msg(text, user, to):
    if 'bot' in text:
        raise NotImplementedError('Working on it...')
