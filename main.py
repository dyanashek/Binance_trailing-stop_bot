import telebot
from binance.client import Client
from binance.enums import *
import numpy
import re
import threading
import time

from keyboards import pnl_keyboard, gap_keyboard

import config

bot = telebot.TeleBot(config.TG_TOKEN)
client = Client(config.BINANCE_FIRST_KEY, config.BINANCE_SECOND_KEY)
allowed_users = config.ALLOWED_USERS.split(', ')
main_user = config.MAIN_USER

start_pnl = config.START_PNL
gap = config.GAP
flag = False
precisions = {}


class Position:
    def __init__(self, symbol, entry_price, mark_price, pnl, side, gap): 
        self.symbol = symbol
        self.entry_price = entry_price
        self.mark_price = mark_price
        self.pnl = pnl
        self.side = side
        precision = precisions[symbol]
        if mark_price != entry_price:
            self.profit = abs(pnl) / (abs(entry_price - mark_price))
        else:
            self.profit = 0
        if self.pnl != 0:
            self.difference = gap * (abs(entry_price - mark_price) / abs(pnl))
            if side == 'LONG':
                self.stop_price = numpy.round((mark_price - self.difference), precision)
            elif side == 'SHORT':
                self.stop_price = numpy.round((mark_price + self.difference), precision)
        else:
            self.difference = 0
            self.stop_price = 0


class Order:
    def __init__(self, symbol, side, stop_price, id, pnl, profit, entry_price): 
        self.symbol = symbol
        self.stop_price = stop_price
        self.side = side
        self.id = id
        self.pnl = pnl
        self.profit = profit
        self.entry_price = entry_price


def stop_trail():
    positions = {}
    orders = {}

    while flag is True:
        begin = time.time()
        try:
            positions_all = client.futures_position_information()
        except:
            positions_all = 0
            reply_text = f'Сбой в работе API Binance.'
            bot.send_message(main_user, reply_text)

        if positions_all != 0:
            prev_symbols = list(positions.keys())
            positions.clear()
            for position in positions_all:
                position_amount = float(position.get('positionAmt'))
                if position_amount != 0:
                    symbol = position.get('symbol')
                    entry_price = float(position.get('entryPrice'))
                    mark_price = float(position.get('markPrice'))
                    pnl = float(position.get('unRealizedProfit'))
                    if position_amount > 0: 
                        side = 'LONG'
                    else:
                        side = 'SHORT'
                    positions[symbol] = Position(symbol, entry_price, mark_price, pnl, side, gap)

            for symbol in prev_symbols:
                if (symbol not in positions) and (symbol in orders):
                    closed_order = orders[symbol]
                    order_pnl_avg = numpy.round(closed_order.pnl, 2)
                    try:
                        params = {
                            'symbol' : symbol,
                            'orderId' : closed_order.id
                        }
                        avg_price = client.futures_get_order(**params).get('avgPrice')
                        if avg_price != 0:
                            diff = avg_price - closed_order.entry_price
                            order_pnl = abs(diff) * closed_order.profit
                            order_pnl = numpy.round(order_pnl, 2)
                        else:
                            order_pnl = 0
                    except:
                        order_pnl = 0
                    
                    if order_pnl == 0:
                        order_pnl = order_pnl_avg
                    orders.pop(symbol)
                    reply_text = f'Сработал трейлинг стоп по паре *{symbol}*,\nPNL составил *{order_pnl} USDT*.'
                    bot.send_message(main_user, reply_text, parse_mode='Markdown')

            for position in positions.values():
                if position.pnl >= start_pnl:
                    if position.symbol not in orders:
                        if position.side == 'LONG':
                            order_side = 'SELL'
                        elif position.side == 'SHORT':
                            order_side = 'BUY'
                        params = {
                            'symbol' : position.symbol,
                            'stopPrice' : position.stop_price,
                            'side' : order_side,
                            'closePosition' : True,
                            'type' : 'STOP_MARKET',
                            'workingType' : 'MARK_PRICE'
                        }
                        try:
                            order = client.futures_create_order(**params)
                        except Exception as ex:
                            order = 0
                            reply_text = f'Не удалось открыть трейлинг стоп по паре *{position.symbol}*.'
                            bot.send_message(main_user, reply_text, parse_mode='Markdown')
                        
                        if order != 0:
                            order_id = order.get('orderId')
                            if order_id is not None:
                                order_pnl = position.pnl - gap
                                orders[position.symbol] = Order(position.symbol, order_side, position.stop_price, order_id, order_pnl, position.profit, position.entry_price)
                                reply_text = f'Открыт трейлинг-стоп по паре *{position.symbol}*.\nPNL: *{numpy.round(position.pnl, 2)} USDT*, отставание *{gap} USDT*.'
                                bot.send_message(main_user, reply_text, parse_mode='Markdown')
                            else:
                                reply_text = f'Не удалось открыть трейлинг стоп по паре *{position.symbol}*.'
                                bot.send_message(main_user, reply_text, parse_mode='Markdown')

                    else:
                        order = orders[position.symbol]
                        prev_id = order.id
                        if (order.side == 'BUY' and order.stop_price > position.stop_price) or\
                              (order.side == 'SELL' and order.stop_price < position.stop_price):
                            
                            if position.side == 'LONG':
                                order_side = 'SELL'
                            elif position.side == 'SHORT':
                                order_side = 'BUY'
                            
                            params = {
                                'symbol' : position.symbol,
                                'stopPrice' : position.stop_price,
                                'side' : order_side,
                                'closePosition' : True,
                                'type' : 'STOP_MARKET',
                                'workingType' : 'MARK_PRICE'
                            }
                            try:
                                new_order = client.futures_create_order(**params)
                            except Exception as ex:
                                new_order = 0
                                reply_text = f'Не удалось изменить трейлинг стоп по паре *{position.symbol}*.'
                                bot.send_message(main_user, reply_text, parse_mode='Markdown')
                            
                            if new_order != 0:
                                order_id = new_order.get('orderId')
                                if order_id is not None:
                                    order_pnl = position.pnl - gap
                                    orders[position.symbol] = Order(position.symbol, order_side, position.stop_price, order_id, order_pnl, position.profit, position.entry_price)
                                    params = {
                                        'symbol' : position.symbol,
                                        'orderId' : prev_id,
                                    }
                                    try:
                                        response = client.futures_cancel_order(**params)
                                    except:
                                        responce = 0
                                        reply_text = f'Не удалось отменить предыдущий ордер по паре *{position.symbol}*.'
                                        bot.send_message(main_user, reply_text, parse_mode='Markdown')

                                    if response != 0:
                                        status = response.get('status')
                                        if status != 'CANCELED':
                                            reply_text = f'Не удалось отменить предыдущий ордер по паре *{position.symbol}*.'
                                            bot.send_message(main_user, reply_text, parse_mode='Markdown')

                                else:
                                    reply_text = f'Не удалось изменить трейлинг стоп по паре *{position.symbol}*.'
                                    bot.send_message(main_user, reply_text, parse_mode='Markdown')

        try:
            open_orders = client.futures_get_open_orders()
        except:
            open_orders = 0
        if open_orders != 0:
            for order in open_orders:
                if order.get('origType') == 'STOP_MARKET' and (order.get('symbol') not in positions):
                    params = {
                        'symbol' : order.get('symbol'),
                        'orderId' : order.get('orderId'),
                    }
                    try:
                        response = client.futures_cancel_order(**params)
                    except:
                        pass

        time.sleep(1)


def form_dict():
    while True:
        try:
            symbols = client.futures_exchange_info().get('symbols')
            for symbol in symbols:
                precisions[symbol.get('symbol')] = int(symbol.get('pricePrecision'))
            bot.send_message(main_user, 'Словарь сформирован.')
        except Exception as ex:
            pass
        time.sleep(86400)


threading.Thread(daemon=True, target=form_dict).start()


@bot.message_handler(commands=['start'])
def start_message(message):
    if str(message.from_user.id) in allowed_users:
        
        start_text = f'''
            \nВоспользуйтесь подходящей командой:\

            \n/pnl X - устанавлиает значение PNL, с которого открывается трейлинг стоп, где Х - значение PNL в USDT;\
            \n/gap N - уcтаналивает отставание трейлинг стопа, где N - значение отставания в USDT;\
            \n/settings - отображает текущие настройки PNL и отставания в USDT;\
            \n/monitor - запускает алгоритм;\
            \n/stop - останавливает алгоритм;\
            \n/status - сообщает статус работы алгоритма;\
            \n/info - сообщает о количестве позцийи открытых в шорт, лонг, а также о марже;\
            \n/help - предоставляет варианты команд.\
        '''
    else:
        start_text = f'Ваш ID: {message.from_user.id}, обратитесь к администратору для предоставления доступа.'
    bot.send_message(message.chat.id, start_text)


@bot.message_handler(commands=['info'])
def start_message(message):
    if str(message.from_user.id) in allowed_users:
        positions = client.futures_account().get('positions')
        long = 0
        short = 0
        long_margin = 0
        short_margin = 0
        for position in positions:
            position_amount = float(position.get('positionAmt'))
            if position_amount != 0:
                margin = float(position.get('positionInitialMargin'))
                if position_amount > 0:
                    long += 1
                    long_margin += margin
                else:
                    short += 1
                    short_margin += margin
        
        long_margin = numpy.round(long_margin, 2)
        short_margin = numpy.round(short_margin, 2)

        reply_text = ''
        if long != 0:
            long_text = f'''
            \nВ лонг открыто позиций: *{long}*,\
            \nМаржа: *{long_margin} USDT*.\
            '''
            reply_text += long_text
        
        if short != 0:
            short_text = f'''
            \nВ шорт открыто позиций: *{short}*,\
            \nМаржа: *{short_margin} USDT*.\
            '''
            reply_text += short_text
        
        if short != 0 and long != 0:
            overall_text = f'''
            \nИтого открыто позиций: *{short + long}*,\
            \nМаржа итого: *{short_margin + long_margin} USDT*.\
            '''
            reply_text += overall_text

        elif short == 0 and long == 0:
            reply_text = 'На данный момент нет открытых позиций.'

        reply_text = reply_text.rstrip('\n')

    else:
        reply_text = f'Ваш ID: {message.from_user.id}, обратитесь к администратору для предоставления доступа.'

    bot.send_message(message.chat.id, reply_text, parse_mode= 'Markdown')


@bot.message_handler(commands=['settings'])
def start_message(message):
    if str(message.from_user.id) in allowed_users:
        reply_text = f'''
        Минимальный PNL: *{start_pnl} USDT*,\nОтставание: *{gap} USDT*.
        '''

    else:
        reply_text = f'Ваш ID: {message.from_user.id}, обратитесь к администратору для предоставления доступа.'

    bot.send_message(message.chat.id, reply_text, parse_mode= 'Markdown')


@bot.message_handler(commands=['help'])
def start_message(message):
    start_text = f'''
            \nВоспользуйтесь подходящей командой:\

            \n/pnl X - устанавливает значение PNL, с которого открывается трейлинг стоп, где Х - значение PNL в USDT;\
            
            \n/gap N - устанавливает отставание трейлинг стопа, где N - значение отставания в USDT;\
            
            \n/settings - отображает текущие настройки PNL и отставания в USDT;\

            \n/monitor - запускает алгоритм;\

            \n/stop - останавливает алгоритм;\

            \n/status - сообщает статус работы алгоритма;\
            
            \n/info - сообщает о количестве позиций открытых в шорт, лонг, а также о марже;\
            
            \n/help - предоставляет варианты команд.\
        '''
    bot.send_message(message.chat.id, start_text)


@bot.message_handler(commands=['pnl'])
def start_message(message):
    if str(message.from_user.id) in allowed_users:
        command_text = message.text.replace(',', '.').lstrip('/pnl').strip('')
        if '.' in command_text:
            regex=r'[0-9]*\.[0-9]'
        else:
            regex = r'[0-9]*'

        try:
            new_pnl = float(('').join(re.findall(regex, command_text)))
        except:
            new_pnl = 0

        if new_pnl >0:
            reply_text = f'Установить PNL в размере *{new_pnl} USDT*?'
            bot.send_message(message.chat.id, reply_text, parse_mode= 'Markdown', reply_markup = pnl_keyboard(new_pnl))
        else:
            reply_text = 'Введен неверный PNL.'
            bot.send_message(message.chat.id, reply_text)

    else:
        reply_text = 'Обратитесь к администратору для получения прав доступа.'
        bot.send_message(message.chat.id, reply_text)


@bot.message_handler(commands=['gap'])
def start_message(message):
    if str(message.from_user.id) in allowed_users:
        command_text = message.text.replace(',', '.').lstrip('/pnl').strip('')

        if '.' in command_text:
            regex=r'[0-9]*\.[0-9]'
        else:
            regex = r'[0-9]*'

        try:
            new_gap = float(('').join(re.findall(regex, command_text)))
        except:
            new_gap = 0

        if new_gap >0:
            reply_text = f'Установить отставание в размере *{new_gap} USDT*?'
            bot.send_message(message.chat.id, reply_text, parse_mode= 'Markdown', reply_markup = gap_keyboard(new_gap))
        else:
            reply_text = 'Введен неверный PNL.'
            bot.send_message(message.chat.id, reply_text)

    else:
        reply_text = 'Обратитесь к администратору для получения прав доступа.'
        bot.send_message(message.chat.id, reply_text)


@bot.message_handler(commands=['monitor'])
def start_message(message):
    if str(message.from_user.id) in allowed_users:
        global flag
        flag = True
        threading.Thread(daemon=True, target=stop_trail).start()
        reply_text = 'Алгоритм запущен.'
    else:
        reply_text = f'Ваш ID: {message.from_user.id}, обратитесь к администратору для предоставления доступа.'
    bot.send_message(message.chat.id, reply_text)


@bot.message_handler(commands=['stop'])
def start_message(message):
    if str(message.from_user.id) in allowed_users:
        global flag
        flag = False
        reply_text = 'Алгоритм остановлен.'
    else:
        reply_text = f'Ваш ID: {message.from_user.id}, обратитесь к администратору для предоставления доступа.'
    bot.send_message(message.chat.id, reply_text)


@bot.message_handler(commands=['status'])
def start_message(message):
    if str(message.from_user.id) in allowed_users:
        if flag is True:
            reply_text = 'Алгоритм активен.'
        else:
            reply_text = 'Алгоритм неактивен.'
        
    else:
        reply_text = f'Ваш ID: {message.from_user.id}, обратитесь к администратору для предоставления доступа.'
    bot.send_message(message.chat.id, reply_text)


@bot.callback_query_handler(func = lambda call: True)
def callback_query(call):
    message_id = call.message.id
    chat_id = call.message.chat.id
    user_id = call.from_user.id
     
    if str(user_id) not in allowed_users:
        reply_text = 'Обратитесь к администратору для получения прав доступа.'
        bot.send_message(chat_id, reply_text)
        return None
    
    call_data = call.data.split('_')
    query = call_data[0]
    new_value = float(call_data[1])

    if query == 'confirmpnl':
        global start_pnl
        start_pnl = new_value
        bot.edit_message_text(chat_id = chat_id, message_id = message_id, text=f'Установален новый PNL *{new_value} USDT*.', parse_mode='Markdown')
    elif query == 'confirmgap':
        global gap
        gap = new_value
        bot.edit_message_text(chat_id = chat_id, message_id = message_id, text=f'Установалено новое отставание *{new_value} USDT*.', parse_mode='Markdown')
    elif query == 'cancel':
        bot.edit_message_text(chat_id = chat_id, message_id = message_id, text=f'Изменения отменены.')


if __name__ == '__main__':
    # bot.polling(timeout=80)
    while True:
        try:
            bot.polling()
        except:
            pass