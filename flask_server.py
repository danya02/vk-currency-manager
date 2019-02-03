import traceback

import vk_api
from flask import Flask, request

from peewee import *
import peewee

db = MySQLDatabase('vkfinance', user='vkfinance', password='12349876')
db.connect()


class BaseModel(Model):
    class Meta:
        database = db


peewee.BaseModel = BaseModel


# import peeweedbevolve


class User(BaseModel):
    user_id = BigIntegerField()
    balance = BigIntegerField(default=0)


class Chat(BaseModel):
    chat_id = BigIntegerField()


class LocalBalance(BaseModel):
    user = ForeignKeyField(User, backref='local_balances')
    balance = BigIntegerField(default=0)
    chat = ForeignKeyField(Chat, backref='balances')


# peeweedbevolve.evolve(db, interactive=False)

db.create_tables([User, Chat, LocalBalance])

app = Flask(__name__)

with open('/var/vk-bots/currency/token.txt') as o:
    token = o.read().strip()


@app.route('/endpoint', methods=['GET', 'POST'])
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
    text = text.lower().split()
    if len(text)==0:return None
    if text[0] == 'money':
        try:
            user_obj = User.get(User.user_id == user)
        except DoesNotExist:
            user_obj = User.create(user_id=user)
        if user == to:  # private chat
            if text[1] == 'balance':
                return 'Your global balance is: ₲' + str(
                    user_obj.balance) + '. To see your local balance, repeat the query inside a chat with the ' \
                                        'community active in the chat. '
            elif text[1] == 'get':
                try:
                    if '-' in text[2] or str(int(text[2])) != text[2]:
                        raise ValueError
                except IndexError:
                    return 'Syntax: money get {int}'
                except ValueError:
                    return 'Value must be a positive integer in its most compact representation.'
                with db.atomic():
                    user_obj.balance += 10
                    user_obj.save()
                    return '£' + str(int(text[2])) + ' GET!'
        else:  # public chat
            try:
                chat = Chat.get(Chat.chat_id == to)

            except DoesNotExist:
                chat = Chat.create(chat_id=to)
            try:
                local_balance = LocalBalance.get(LocalBalance.user == user_obj, LocalBalance.chat == chat)

            except DoesNotExist:
                local_balance = LocalBalance.create(user=user_obj, chat=chat)
            if text[1] == 'balance':
                return 'Your local balance for this chat (id ' + str(chat.chat_id) + ') is: £' + str(
                    local_balance.balance) + '. To see your global balance, start a private chat with this community.'
            elif text[1] == 'get':
                try:
                    if '-' in text[2] or str(int(text[2])) != text[2]:
                        raise ValueError
                except IndexError:
                    return 'Syntax: money get {int}'
                except ValueError:
                    return 'Value must be a positive integer in its most compact representation.'
                with db.atomic():
                    local_balance.balance += int(text[2])
                    local_balance.save()
                    return '£' + str(int(text[2])) + ' GET!'

        return 'Command "' + text[1] + '" is not valid, valid commands are: balance, get.'
