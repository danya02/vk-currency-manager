import traceback

import vk_api
from flask import Flask, request

app = Flask(__name__)

with open('/var/vk-bots/currency/token.txt') as o:
    token = o.read().strip()


@app.route('/endpoint', methods=['POST'])
def main():
    try:
        data = request.get_json(force=True)
    except:
        return 'bad json: ' + str(request.data, 'utf-8'), 400
    if data['type'] == 'confirmation':
        return 'caf10767'
    if data['type'] != 'message_new':
        return 'wrong type', 400
    obj = data['object']
    text = obj['text']
    user = obj['from_id']
    if 'peer_id' in obj:
        to = obj['peer_id']
    else:
        to = user
    try:
        msg = process_msg(text, user, to)
    except:
        msg = 'Sorry, an exception occurred while processing your request.\n' + traceback.format_exc()
    if msg is not None:
        session = vk_api.VkApi(token=token)
        api = session.get_api()
        api.messages.send(peer_id=to, message=msg, random_id=0)
    return 'ok'


def process_msg(text, user, to):
    if 'bot' in text:
        return "Recv'd message from " + str(user) + ", responding to " + str(to) + " re text: '" + text + "'."
