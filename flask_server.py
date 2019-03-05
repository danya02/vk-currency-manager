import base64
import traceback

import peewee
import vk_api
from flask import Flask, request, render_template
from peewee import *
import requests
import rsa
import datetime

import abc

db = MySQLDatabase('vkfinance', user='vkfinance', password='12349876')
db.connect()


class BaseModel(Model):
    class Meta:
        database = db


peewee.BaseModel = BaseModel

# import peeweedbevolve


GLOBAL_SYMB = '₲'
LOCAL_SYMB = '£'
MINING_DIFF = 16384


class User(BaseModel):
    user_id = BigIntegerField(unique=True)
    balance = BigIntegerField(default=0)


class Chat(BaseModel):
    chat_id = BigIntegerField(unique=True)


class LocalBalance(BaseModel):
    user = ForeignKeyField(User, backref='local_balances')
    balance = BigIntegerField(default=0)
    chat = ForeignKeyField(Chat, backref='balances')


class Peer(BaseModel):
    respond_to = TextField()
    public_key = BlobField()
    balance = BigIntegerField(default=0)


class LocalBotBalance(BaseModel):
    peer = ForeignKeyField(Peer, backref='local_balances')
    balance = BigIntegerField(default=0)
    chat = ForeignKeyField(Chat, backref='bot_balances')


class HumanTransaction(BaseModel):
    source = ForeignKeyField(User, null=True)
    dest = ForeignKeyField(User, null=True)
    amount = BigIntegerField()
    chat = ForeignKeyField(Chat, null=True)
    date = DateTimeField(default=datetime.datetime.now)


class BotTransaction(BaseModel):
    human = ForeignKeyField(User)
    bot = ForeignKeyField(Peer)
    is_to_bot = BooleanField()
    amount = BigIntegerField()
    chat = ForeignKeyField(Chat, null=True)
    date = DateTimeField(default=datetime.datetime.now)


# peeweedbevolve.evolve(db, interactive=False)

db.create_tables([User, Chat, LocalBalance, Peer])

app = Flask(__name__)

with open('/var/vk-bots/currency/token.txt') as o:
    token = o.read().strip()

with open('/var/vk-bots/currency/coinhive-token.txt') as o:
    coinhive_token = o.read().strip()

with open('/var/vk-bots/currency/secretkey.pem', 'rb') as o:
    my_secret_key = rsa.PrivateKey.load_pkcs1(o.read())


def send(to, msg):
    session = vk_api.VkApi(token=token)
    api = session.get_api()
    api.messages.send(peer_id=to, message=msg, random_id=0)


def repr_user(user_id):
    session = vk_api.VkApi(token=token)
    api = session.get_api()
    data = api.users.get(user_ids=user_id, fields='screen_name')[0]
    return data['first_name'] + ' ' + data['last_name'] + ' (@' + data['screen_name'] + ')'


@app.route('/')
def index():
    return render_template('index.html')


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
        send(to, msg)
    return 'ok'


class Type(metaclass=abc.ABCMeta):
    def __init__(self, description=None, optional=False):
        self.description = description
        self.optional = optional

    def parse(self, value):
        raise NotImplementedError

    def is_val_ok(self, value):
        raise NotImplementedError

    def short_name(self):
        raise NotImplementedError

    def long_name(self):
        raise NotImplementedError


class Integer(Type):
    def parse(self, value):
        return int(value)

    def is_val_ok(self, value):
        try:
            int(value)
            return True
        except:
            return False

    def short_name(self):
        return 'int'

    def long_name(self):
        return 'Integer'


class PositiveInteger(Integer):
    def short_name(self):
        return 'int(>0)'

    def long_name(self):
        return 'Integer greater than 0'

    def is_val_ok(self, value):
        if super().is_val_ok(value):
            return super().parse(value) > 0
        else:
            return False


class IntegerInRange(Integer):
    def __init__(self, a, b, description=None, optional=False):
        super().__init__(description, optional)
        self.range = range(a, b)

    def is_val_ok(self, value):
        if super().is_val_ok(value):
            return super().parse(value) in self.range

    def short_name(self):
        return 'int(>=' + str(self.range.start) + '&&<' + str(self.range.stop) + ')'

    def long_name(self):
        return 'Integer in range [' + str(self.range.start) + '; ' + str(self.range.stop) + ')'


class ChatID(PositiveInteger):
    def short_name(self):
        return 'chat_id'

    def long_name(self):
        return 'Chat ID (get your own with the "id" command)'

    def is_val_ok(self, value):
        if super().is_val_ok(value):
            return Chat.get_or_none(Chat.chat_id == super().parse(value)) is not None


class String(Type):
    def parse(self, value):
        return value

    def short_name(self):
        return 'str'

    def long_name(self):
        return 'String'

    def is_val_ok(self, value):
        return True


class UserMention(String):
    def short_name(self):
        return 'mention'

    def long_name(self):
        return 'User @-mention (example: @durov)'

    def is_val_ok(self, value):
        try:
            value = value.split('@')[1].replace('[', '').replace(']', '').replace('|', '')
            session = vk_api.VkApi(token=token)
            api = session.get_api()
            api.users.get(user_ids=value)
            return True
        except:
            return False

    def parse(self, value):
        value = value.split('@')[1].replace('[', '').replace(']', '').replace('|', '')
        session = vk_api.VkApi(token=token)
        api = session.get_api()
        return api.users.get(user_ids=value)[0]['id']


class Base64(String):

    def parse(self, value):
        return base64.b64decode(bytes(value, 'utf-8'))

    def is_val_ok(self, value):
        try:
            base64.b64decode(bytes(value, 'utf-8'))
        except:
            return False

    def short_name(self):
        return 'base64'

    def long_name(self):
        return 'Binary data encoded in Base64'


def params(*parameters):
    def decorator(func):
        num_reqired = 0
        req = True
        for i in parameters:
            if i.optional:
                req = False
            else:
                if not req:
                    raise AttributeError('In decorator definition, non-optional argument follows optional argument.')
                num_reqired += 1

        def decorated_func(user_id, respond_to, *args):
            args = args[0]
            if len(args) < num_reqired:
                return 'Not enough arguments: expecting at least ' + str(num_reqired) + ', found ' + str(
                    len(args)) + ' instead.'
            if len(args) > len(parameters):
                return 'Too many arguments: expecting at most ' + str(len(parameters)) + ', found ' + str(
                    len(args)) + ' instead.'
            parsed_args = []
            for n, i, j in zip(range(len(args)), args, parameters):
                if not j.is_val_ok(i):
                    return 'Argument ' + str(n + 1) + ' (' + repr(i) + ') is not a valid ' + j.long_name() + '.'
                parsed_args.append(j.parse(i))
            return func(user_id, respond_to, *parsed_args)

        syntax_str = ''
        depth = 0
        for i in parameters:
            if i.optional:
                depth += 1
                syntax_str += '[' + i.short_name() + (':' + i.description if i.description else '') + ' '
            else:
                syntax_str += '{' + i.short_name() + (':' + i.description if i.description else '') + '} '
        syntax_str = syntax_str.strip()
        syntax_str += ']' * depth
        decorated_func.syntax_str = syntax_str
        decorated_func.__doc__ = func.__doc__
        return decorated_func

    return decorator


def description(desc):
    def decorator(func):
        def decorated_func(*args, **kwargs):
            return func(*args, **kwargs)

        decorated_func.description = desc
        return decorated_func

    return decorator


@params(ChatID(optional=True))
def balance(user_id, respond_to, chat_id=None):
    """Get your balance. If the optional chat ID is set, get your balance for that chat instead of this one."""
    user, created = User.get_or_create(user_id=user_id)
    if chat_id is None:
        if user_id == respond_to:
            return 'Your global balance is: ' + GLOBAL_SYMB + str(user.balance)
        else:
            chat, chat_created = Chat.get_or_create(chat_id=respond_to)
            local_balance, localb_created = LocalBalance.get_or_create(user=user, chat=chat)
            return 'Your local balance is: ' + LOCAL_SYMB + str(local_balance.balance) + '.'
    else:
        if respond_to != user_id and chat_id != respond_to:
            return 'It is unsafe to check balance for a chat different to your own. Please start a chat with this ' \
                   'community and repeat your query.'
        else:
            chat, chat_created = Chat.get_or_create(chat_id=chat_id)
            local_balance, localb_created = LocalBalance.get_or_create(user=user, chat=chat)
            return 'Your local balance for chat ' + str(chat_id) + ' is: ' + LOCAL_SYMB + str(
                local_balance.balance) + '.'


@params()
def chat_id(user_id, respond_to):
    """Check this chat's ID. This ID can later be used to get your balance without being in the chat, and to convert
    global balance to that chat's local balance. """
    if user_id == respond_to:
        return 'This is the private chat between you and this community; it has no ID. You must use this chat to ' \
               'manage your global balance. '
    else:
        return 'This chat has an ID of ' + str(
            respond_to) + '. This is the ID to use to convert global balance to local ' \
                          'balance and to check your balance privately.'


@params(UserMention('destination user'), PositiveInteger('amount to transfer'), String('confirmation', True))
def transfer(user_id, respond_to, dest_user, amt_transfer, confirm=None):
    """Give some currency of this chat to another user."""
    user, created = User.get_or_create(user_id=user_id)
    if respond_to == user_id:
        if confirm != 'Confirm':
            return 'You are requesting to transfer ' + GLOBAL_SYMB + str(amt_transfer) + ' from you to ' + \
                   repr_user(dest_user) + \
                   '. If this is what you wanted to do, write "Confirm" without quotes after the amount to ' \
                   'transfer and repeat your query.'
        if user.balance >= amt_transfer:
            other_user, other_user_created = User.get_or_create(user_id=dest_user)
            with db.atomic():
                user.balance -= amt_transfer
                other_user.balance += amt_transfer
                user.save()
                other_user.save()
                HumanTransaction.create(chat=None, amount=amt_transfer,
                                        source=user, dest=other_user)

            if other_user_created:
                msg = 'User ' + repr_user(user_id) + ' has just transferred ' + GLOBAL_SYMB + str(
                    amt_transfer) + ' to you via the Currency manager bot.'
            else:
                msg = 'Received ' + GLOBAL_SYMB + str(amt_transfer) + ' from ' + repr_user(user_id) + '.'
            note = ''
            try:
                send(dest_user, msg)
            except:
                note = 'However, because that user did not start a chat with this community, the notification failed. ' \
                       'You will have to inform them manually. '
            return 'Transferred ' + GLOBAL_SYMB + str(amt_transfer) + ' to ' + repr_user(dest_user) + '. ' + note
        else:
            return 'Insufficient funds to transfer.'
    else:
        if confirm not in ['ForceConfirm', 'Confirm']:
            return 'You are requesting to transfer ' + LOCAL_SYMB + str(amt_transfer) + ' from you to ' + repr_user(
                dest_user) + \
                   '. If this is what you wanted to do, write "Confirm" without quotes after the amount to ' \
                   'transfer and repeat your query.'
        other_user, other_user_created = User.get_or_create(user_id=dest_user)
        chat, chat_created = Chat.get_or_create(chat_id=respond_to)
        other_local_balance = LocalBalance.get_or_none(LocalBalance.chat == chat, LocalBalance.user == other_user)
        if other_local_balance is None:
            if confirm != 'ForceConfirm':
                return 'Attention: The target user, ' + repr_user(dest_user) + ', has no database entry for this ' \
                                                                               'chat.  This means that user has never ' \
                                                                               'performed any interaction with this ' \
                                                                               'bot in this chat. If you ' \
                                                                               'wish to transfer anyway, repeat your ' \
                                                                               'query, replacing "Confirm" with ' \
                                                                               '"ForceConfirm".'
            other_local_balance = LocalBalance.create(user=other_user, chat=chat)
        my_local_balance, _ = LocalBalance.get_or_create(user=user, chat=chat)
        if my_local_balance.balance >= amt_transfer:
            with db.atomic():
                my_local_balance.balance -= amt_transfer
                other_local_balance.balance += amt_transfer
                my_local_balance.save()
                other_local_balance.save()
                HumanTransaction.create(chat=chat, amount=amt_transfer,
                                        source=user, dest=other_user)

            return 'Transferred ' + LOCAL_SYMB + str(amt_transfer) + ' to ' + repr_user(dest_user) + '.'
        else:
            return 'Insufficient funds to transfer.'


@params(PositiveInteger('amount to convert'), ChatID('target chat'), String('confirmation', True))
def convert(user_id, respond_to, amt, chat_id, confirm=None):
    """Convert some global currency to local currency of this chat. Note, this operation is irreversible."""
    if user_id != respond_to:
        return 'You must be in a private chat with this community to perform this action.'
    user, _ = User.get_or_create(user_id=user_id)
    if user.balance < amt:
        return 'Insufficient funds in global currency to complete the conversion.'
    if confirm != 'Confirm':
        return 'You are requesting to convert ' + GLOBAL_SYMB + str(amt) + ' to ' + LOCAL_SYMB + str(amt) + \
               ' in chat ' + str(
            chat_id) + '. If this is what you wanted to do, write "Confirm" without quotes after the ' \
                       'amount to convert and repeat your query. '
    chat = Chat.get(Chat.chat_id == chat_id)
    local_balance = LocalBalance.get(LocalBalance.user == user, LocalBalance.chat == chat)
    with db.atomic():
        user.balance -= amt
        local_balance.balance += amt
        user.save()
        local_balance.save()
    HumanTransaction.create(chat=None, amount=amt,
                            source=user, dest=None)
    HumanTransaction.create(chat=chat, amount=amt,
                            source=None, dest=user)

    return 'Conversion completed.'


@params()
def withdraw(user_id, respond_to):
    '''Redeem global currency earned through mining.'''
    answer = requests.get(
        "https://api.coinhive.com/user/balance?secret=" + coinhive_token + '&name=' + str(user_id)).json()
    if not answer['success']:
        return 'Getting your crypto-balance failed. The server response was: ' + str(
            answer) + '\nMost likely this means you haven\'t started mining yet. Visit this community\'s page to go to the mining page.'
    balance_add = (answer['balance'] // MINING_DIFF)
    if balance_add == 0:
        return 'Not enough hashes to convert to global currency: you have ' + str(
            answer['balance']) + ' hashes. Mine more, the exchange rate is ' + str(
            MINING_DIFF) + ' hashes per ' + GLOBAL_SYMB + '1.'
    if requests.post("https://api.coinhive.com/user/withdraw",
                     data={'secret': coinhive_token, 'name': str(user_id), 'amount': balance_add * MINING_DIFF}).json()[
        'success']:
        with db.atomic():
            user = User.get(User.user_id == user_id)
            user.balance += balance_add
            user.save()
            HumanTransaction.create(chat=None, amount=balance_add,
                                    source=None, dest=user)
            return 'Your global balance has been increased by ' + GLOBAL_SYMB + str(balance_add) + '.'
    else:
        return 'A problem occurred while getting your balance from the Coinhive server.'


@params(String('peer'), Base64('data'))
def transaction(user, to, peer, data):
    """Perform a bot transaction. Only for use by bots, not to be used by humans."""
    if user == to:
        return 'This command must not be used by humans.'
    peer = Peer.get_or_none(Peer.respond_to == peer)
    if peer is None:
        return 'This peer is unknown. This likely means that the calling bot has been misconfigured, or a ' \
               'malicious user is masquerading as a bot.'
    peerkey = rsa.PublicKey.load_pkcs1(peer.public_key)
    try:
        data = rsa.decrypt(data, my_secret_key)
    except:
        return 'Decryption failed. This likely means that the calling bot has been misconfigured, or a ' \
               'malicious user is masquerading as a bot.'
    # TODO: add logic
    response = rsa.encrypt(b'not impl', peerkey)
    return peer.respond_to + ' transaction_answer ' + str(base64.b64encode(response), 'utf-8')


def process_msg(text, user, to):
    try:
        text = text.split()
        text[0] = text[0].lower()
    except:
        return None
    cmds = {'balance': balance, 'id': chat_id, 'send': transfer, 'convert': convert, 'withdraw': withdraw}
    if len(text) == 0: return None
    if text[0] == 'money' or user == to:
        if text[0] == 'money':
            text.pop(0)
        if text[0] == 'help':
            text.pop(0)
            if len(text) == 0:
                return 'This is the currency management bot. To get a list of commands, repeat this command. replacing' \
                       ' "help" with any word. To get help for a command, type the full path to the command after' \
                       ' "help".'
            else:
                path = ['money'] if user != to else []
                cur_level = cmds
                while not callable(cur_level):
                    try:
                        this_lvl_cmd = text.pop(0).lower()
                    except IndexError:
                        return 'Command expected. Available commands are: ' + ' '.join(path) + ' {' + ', '.join(
                            cur_level) + '}.'
                    path.append(this_lvl_cmd)
                    if this_lvl_cmd in cur_level:
                        cur_level = cur_level[this_lvl_cmd]
                    else:
                        return 'This command does not exist. Available commands are: ' + ' '.join(path[:-1]) + ' {' + \
                               ', '.join(cur_level) + '}.'

                return 'Syntax: ' + ' '.join(path) + ' ' + cur_level.syntax_str + (
                    ('\n' + cur_level.__doc__) if cur_level.__doc__ else '')

        path = ['money'] if user != to else []
        cur_level = cmds
        while not callable(cur_level):
            try:
                this_lvl_cmd = text.pop(0)
            except IndexError:
                return 'Command expected. Available commands are: ' + ' '.join(path) + ' {' + ', '.join(
                    cur_level) + '}.'
            path.append(this_lvl_cmd)
            if this_lvl_cmd in cur_level:
                cur_level = cur_level[this_lvl_cmd]
            else:
                return 'This command does not exist. Available commands are: ' + ' '.join(path[:-1]) + ' {' + \
                       ', '.join(cur_level) + '}.'

        return cur_level(user, to, text)
