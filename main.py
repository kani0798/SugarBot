import telebot
from telebot import types, util
from flask import Flask, request
import logging

import re
import json
import random
import os

TOKEN = '5322038221:AAFPdj5T4vVnr9DvBMHLFkdGAvc6t4VTejk'
URL = f'https://sugar-blood-bot.herokuapp.com/{TOKEN}'
admin = 427446631

bot = telebot.TeleBot(TOKEN)
server = Flask(__name__)

action_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
btn1 = types.KeyboardButton('🗒️ Все разделы')
btn2 = types.KeyboardButton('🔍 Поиск темы')
action_keyboard.add(btn1, btn2)

dostup = types.InlineKeyboardMarkup(row_width=1)
btn3 = types.InlineKeyboardButton('🔓 Получить доступ', url='https://wa.me/996701116363?text=')
dostup.add(btn3)


current_tags = {}


def is_admin(func):
    def wrapper(message):
        if message.chat.id == admin:
            func(message)
        else:
            bot.send_message(message.chat.id, '🚫')
    return wrapper


def load_user(username):
    with open('users.json') as file:
        users = json.load(file)
        has_perm = [user['username'] for user in users if user['username'] == username]
        return has_perm


def has_permission(func):
    def wrapper(message):
        username = message.chat.username
        has_perm = load_user(username)
        if has_perm:
            func(message)
        else:
            pass
    return wrapper


def get_tags():
    tag_keyboard = types.InlineKeyboardMarkup(row_width=1)
    with open('content.json') as f:
        data = json.load(f)
        tags = {dct['tag'] for dct in data}
        for tag in tags:
            tag_keyboard.add(types.InlineKeyboardButton(tag.capitalize(), callback_data=f'Tag:{tag}'))
    return tag_keyboard


def get_themes(tag):
    with open('content.json') as f:
        data = json.load(f)
        themes = [(d['theme'], d['id']) for d in data if d['tag'] == tag]
        return themes


def paginate_themes(themes):
    theme_keyboard = types.InlineKeyboardMarkup(row_width=1)
    for theme, id in themes:
        theme_keyboard.add(types.InlineKeyboardButton(theme, callback_data=f'Theme:{id}'))
    return theme_keyboard


@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    has_perm = load_user(message.chat.username)
    if has_perm:
        bot.send_message(chat_id,
                         f"Здравствуйте {message.chat.first_name if message.chat.first_name else message.chat.username}!\nЯ Диабет-бот помощник😊 Расскажу вам всё, что касается Сахарного Диабета\nВыберите действие⏬",
                         reply_markup=action_keyboard)
    else:
        bot.send_message(chat_id,
                         f"Здравствуйте {message.chat.first_name if message.chat.first_name else message.chat.username}!\nЯ Диабет-бот помощник😊 Расскажу вам всё, что касается Сахарного Диабета\nВыберите действие⏬",
                         reply_markup=dostup)


@bot.message_handler(regexp='🗒️ Все разделы')
@has_permission
def handle_themes_query(message):
    chat_id = message.chat.id
    markup = get_tags()
    bot.send_message(chat_id, 'Выберите интересующий вас раздел', reply_markup=markup)


@bot.message_handler(regexp='🔍 Поиск темы')
@has_permission
def handle_themes_query_myself(message):
    chat_id = message.chat.id
    msg = bot.send_message(chat_id, 'Введите тему')
    bot.register_next_step_handler(msg, handle_theme_myself)


def handle_theme_myself(message):
    chat_id = message.chat.id
    theme = message.text
    current_tags[chat_id] = None
    with open('content.json') as f:
        data = json.load(f)
        data_with_hashtags = [dct for dct in data if dct.get('hashtags')]
        themes = {(dct['theme'], dct['id']) for dct in data
                  if bool(re.search(theme, dct['theme'], flags=re.IGNORECASE))}
        added = {(dct['theme'], dct['id']) for dct in data_with_hashtags
                 if theme.lower() in dct['hashtags']}
        themes.update(added)
    if themes:
        theme_keyboard = paginate_themes(themes)
        bot.send_message(chat_id, 'Выберите конкретную тему', reply_markup=theme_keyboard)
    else:
        bot.send_message(chat_id, 'Тема не найдена. Попробуйте еще раз', reply_markup=action_keyboard)


@bot.callback_query_handler(func=lambda call: call.data.startswith('Tag:'))
def handle_theme_query(call):
    chat_id = call.message.chat.id
    tag = call.data.split('Tag:')[-1].lower()
    if not current_tags.get(chat_id):
        current_tags[chat_id] = {"tag": tag, "start": 0, "end": 10}
    themes = get_themes(current_tags[chat_id]['tag'])
    if len(themes) > 10:
        markup = paginate_themes(themes[current_tags[chat_id]['start']: current_tags[chat_id]['end']])
        markup.row_width = 2
        markup.add(types.InlineKeyboardButton('⏮', callback_data='prev'),
                   types.InlineKeyboardButton('⏭️', callback_data='next'))
        bot.delete_message(chat_id, call.message.message_id)
        bot.send_message(chat_id, 'Выберите конкретную тему', reply_markup=markup)
    else:
        markup = paginate_themes(themes)
        bot.delete_message(chat_id, call.message.message_id)
        bot.send_message(chat_id, 'Выберите конкретную тему', reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data in ['next', 'prev'])
def handle_next_prev(call):
    chat_id = call.message.chat.id
    if call.data == 'next':
        current_tags[chat_id]['start'] += 10
        current_tags[chat_id]['end'] += 10
    if call.data == 'prev':
        current_tags[chat_id]['start'] -= 10
        current_tags[chat_id]['end'] -= 10
    themes = get_themes(current_tags[chat_id]['tag'])
    markup = paginate_themes(themes[current_tags[chat_id]['start']: current_tags[chat_id]['end']])
    markup.row_width = 2
    markup.add(types.InlineKeyboardButton('⏮', callback_data='prev'),
               types.InlineKeyboardButton('⏭️', callback_data='next'))
    bot.edit_message_text('Выберите конкретную тему', call.from_user.id, call.message.message_id,
                          reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith('Theme:'))
def handle_theme(call):
    chat_id = call.message.chat.id
    theme = call.data.split('Theme:')[-1]
    with open('content.json') as f:
        themes = json.load(f)
        thema = [dict_ for dict_ in themes if dict_['id'] == int(theme)][0]
    try:
        current_tags.pop(chat_id)
    except:
        pass
    bot.delete_message(chat_id, call.message.message_id)
    if len(thema['description']) > 4095:
        bot.send_message(chat_id, f'<b><i>{thema["theme"]}</i></b>', parse_mode='html')
        splitted_text = util.split_string(thema['description'], chars_per_string=3000)
        for text in splitted_text:
            bot.send_message(chat_id, text)
    else:
        bot.send_message(chat_id, f'<b><i>{thema["theme"]}</i></b>\n{thema["description"]}', parse_mode='html')
    if thema.get('image'):
        curr_dir = f'{os.path.abspath(os.curdir)}/images'
        for img in thema.get('image'):
            bot.send_photo(chat_id, photo=open(f"{curr_dir}/{img}", 'rb'))


# Add new Post
new_theme = {}


@bot.message_handler(commands=['add'])
@is_admin
def add(message):
    msg = bot.send_message(admin, 'Создаем новый пост!\nПришлите свой новый пост в формате:\n1. Раздел\n2. Название темы\n3. Описание\n4. Ссылка на видео (если есть)\nЕсли есть картинки, можете отправить их после поста')
    bot.register_next_step_handler(msg, add_option)


def save_post(post:dict):
    if post == {}:
        raise ValueError
    with open('content.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        max_id = max([d['id'] for d in data])
        post['id'] = max_id + 1
        data.append(post)
    with open('content.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def add_option(message):
    try:
        post = message.text.split("\n")
        new_theme['tag'] = re.sub(' +', ' ', post[0].lower().strip())
        new_theme['theme'] = re.sub(' +', ' ', post[1].capitalize().strip())
        new_theme['description'] = '\n'.join(post[2:])
        new_theme['image'] = []
    except:
        bot.send_message(admin, 'Неправильный формат')


@bot.message_handler(content_types=['photo'])
@is_admin
def photo(message):
    try:
        fileID = message.photo[-1].file_id
        file_info = bot.get_file(fileID)
        downloaded_file = bot.download_file(file_info.file_path)
        img_name = new_theme['theme'].replace(' ', '+').lower() + str(random.randint(99, 999))
        new_theme['image'].append(img_name+'.jpg')
        with open(f"images/{img_name}.jpg", 'wb') as new_file:
            new_file.write(downloaded_file)
    except:
        pass


@bot.message_handler(commands=['save'])
@is_admin
def save(message):
    try:
        assert 'tag' and 'theme' and 'description' in new_theme.keys()
        save_post(new_theme)
        new_theme.clear()
        bot.send_message(admin, 'Новый пост успешно сохранен')
    except ValueError:
        bot.send_message(admin, 'Нечего сохранять')
    except:
        bot.send_message(admin, 'Что-то пошло не так...')


@bot.message_handler(commands=['delete'])
@is_admin
def update(message):
    msg = bot.send_message(admin, 'Какую тему вы хотите удалить?')
    bot.register_next_step_handler(msg, update_post)


def update_post(message):
    theme = re.sub(' +', ' ', message.text.capitalize().strip())
    try:
        with open('content.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            theme_to_edit = [d for d in data if d['theme'] == theme][0]
            data.remove(theme_to_edit)
        with open('content.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        bot.send_message(admin, 'Тема успешно удалена')
    except:
        bot.send_message(admin, 'Такой темы нет')


# Add new User
@bot.message_handler(commands=['user'])
@is_admin
def update(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    btn1 = types.KeyboardButton('Добавить')
    btn2 = types.KeyboardButton('Удалить')
    markup.add(btn1, btn2)
    msg = bot.send_message(admin, 'Вы хотите добавить или удалить пользователя?', reply_markup=markup)
    bot.register_next_step_handler(msg, user_action)


@is_admin
def user_action(message):
    if message.text == 'Добавить':
        msg = bot.send_message(admin, 'Введите username нового пользователя')
        bot.register_next_step_handler(msg, add_user)

    elif message.text == 'Удалить':
        msg = bot.send_message(admin, 'Введите username пользователя для удаления')
        bot.register_next_step_handler(msg, delete_user)


def add_user(message):
    try:
        if message.text.startswith('@'):
            user = message.text.replace('@', '', 1)
        else:
            user = message.text
        with open('users.json') as file:
            users = json.load(file)
            users.append({"username": user})
        with open('users.json', 'w') as file:
            json.dump(users, file, ensure_ascii=False, indent=4)
        bot.send_message(admin, f'{user} Успешно добавлен')
    except:
        bot.send_message(admin, 'Не получилось добавить')


def delete_user(message):
    try:
        if message.text.startswith('@'):
            user = message.text.replace('@', '', 1)
        else:
            user = message.text
        with open('users.json') as file:
            users = json.load(file)
            users.remove({"username": user})
        with open('users.json', 'w') as file:
            json.dump(users, file, ensure_ascii=False, indent=4)
        bot.send_message(admin, f'{user} Успешно удален')
    except:
        bot.send_message(admin, 'Такого пользователя нет')


# @server.route("/bot", methods=['POST'])
# def getMessage():
#     bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
#     return "!", 200
#
# @server.route("/")
# def webhook():
#     bot.remove_webhook()
#     bot.set_webhook(url=URL) # этот url нужно заменить на url вашего Хероку приложения
#     return "?", 200

# server.run(host="0.0.0.0", port=os.environ.get('PORT', 80))


bot.infinity_polling()



