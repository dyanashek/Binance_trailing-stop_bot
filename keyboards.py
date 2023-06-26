from telebot import types

def pnl_keyboard(new_pnl):
    pnl_keyboard = types.InlineKeyboardMarkup()
    confirm = types.InlineKeyboardButton('Подтвердить', callback_data = f'confirmpnl_{new_pnl}')
    cancel = types.InlineKeyboardButton('Отменить', callback_data = f'cancel_{new_pnl}')
    pnl_keyboard.add(confirm)
    pnl_keyboard.add(cancel)
    return pnl_keyboard

def gap_keyboard(new_gap):
    gap_keyboard = types.InlineKeyboardMarkup()
    confirm = types.InlineKeyboardButton('Подтвердить', callback_data = f'confirmgap_{new_gap}')
    cancel = types.InlineKeyboardButton('Отменить', callback_data = f'cancel_{new_gap}')
    gap_keyboard.add(confirm)
    gap_keyboard.add(cancel)
    return gap_keyboard