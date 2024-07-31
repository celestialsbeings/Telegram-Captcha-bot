import telebot
from telebot import types
import random
import sqlite3
from PIL import Image, ImageDraw, ImageFont
import os
import math
from keep_alive import keep_alive
keep_alive()

# إعداد توكن البوت ومعرّف القنوات
BOT_TOKEN = '7498690398:AAGlifuFPAEOGFVeWZbsSJ9glhSvybBVw_s'
CHANNEL_ID_1 = -1002065513632
CHANNEL_ID_2 = -1002231664917  # اضف معرف القناة الثانية هنا
ADMIN_ID = '6265624550'

bot = telebot.TeleBot(BOT_TOKEN)

user_data = {}

def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, received_link BOOLEAN)''')
    conn.commit()
    conn.close()

def check_user(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT received_link FROM users WHERE user_id = ?', (user_id,))
    result = c.fetchone()
    conn.close()
    if result:
        return result[0]
    return False

def set_user_received_link(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO users (user_id, received_link) VALUES (?, ?)', (user_id, True))
    conn.commit()
    conn.close()

def generate_random_numbers():
    return random.sample(range(10), 5)

WIDTH, HEIGHT = 400, 200

def draw_wavy_line(draw, width, height, line_width, angle):
    amplitude = 10
    frequency = 3
    num_points = width
    offset = height // 2
    for x in range(0, num_points, 2):
        y = int(offset + amplitude * math.sin(frequency * (x / num_points) * 2 * math.pi) + (angle * x / num_points))
        draw.line([(x, y), (x + 2, y)], fill='black', width=line_width)

def distort_text(draw, text, font, start_x, start_y):
    x = start_x
    y = start_y
    for char in text:
        angle = random.uniform(-15, 10)
        draw.text((x, y), char, font=font, fill='black', stroke_width=1)
        char_bbox = draw.textbbox((x, y), char, font=font)
        char_width = char_bbox[2] - char_bbox[0]
        char_height = char_bbox[3] - char_bbox[1]
        x += char_width
        y += random.uniform(-10, 5)

def create_image_with_numbers(numbers):
    img = Image.new('RGB', (WIDTH, HEIGHT), color='white')
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype("arial.ttf", 120) 

    text = ' '.join(map(str, numbers))
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    text_x = (WIDTH - text_width) // 2
    text_y = (HEIGHT - text_height) // 20

    distort_text(draw, text, font, text_x, text_y)

    draw_wavy_line(draw, WIDTH, HEIGHT, line_width=20, angle=+50)

    image_path = f'numbers_{random.randint(0, 10000)}.png'
    img.save(image_path)
    return image_path

def create_number_markup():
    markup = types.InlineKeyboardMarkup()
    
    numbers = list(range(1, 10))
    rows = [numbers[i:i + 3] for i in range(0, len(numbers), 3)]
    for row in rows:
        buttons = [types.InlineKeyboardButton(str(num), callback_data=f'num_{num}') for num in row]
        markup.add(*buttons)
    
    markup.add(
        types.InlineKeyboardButton('reset', callback_data='change'),
        types.InlineKeyboardButton('0', callback_data='num_0'),
        types.InlineKeyboardButton('clear', callback_data='delete')
    )
    
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.chat.id
    if check_user(user_id):
        bot.send_message(user_id, 'You already got the link!')
        return

    random_numbers = generate_random_numbers()
    image_path = create_image_with_numbers(random_numbers)
    with open(image_path, 'rb') as image_file:
        msg = bot.send_photo(user_id, image_file, caption='Caution captcha has 5 numbers! If you dont see all of them please click image. Pass Captcha')

    user_data[user_id] = {
        'random_numbers': random_numbers,
        'selected_numbers': []
    }

    markup = create_number_markup()
    
    bot.edit_message_caption(caption='Caution captcha has 5 numbers! If you dont see all of them please click image. Pass Captcha', chat_id=user_id, message_id=msg.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.message.chat.id
    data = call.data.split('_')

    if len(data) < 2:
        bot.answer_callback_query(call.id, 'Wrong data')
        return

    action = data[0]
    item = data[1]

    if user_id not in user_data:
        bot.answer_callback_query(call.id, 'Data not available')
        return

    user_data_entry = user_data[user_id]
    if action == 'num':
        try:
            number = int(item)
            selected_numbers = user_data_entry['selected_numbers']

            if number not in selected_numbers:
                selected_numbers.append(number)

            new_message = ' '.join(map(str, selected_numbers))

            correct_numbers = user_data_entry['random_numbers']

            if len(selected_numbers) == len(correct_numbers):
                if selected_numbers == correct_numbers:
                    if not check_user(user_id):
                        invite_link_1 = bot.create_chat_invite_link(CHANNEL_ID_1, member_limit=1).invite_link
                        invite_link_2 = bot.create_chat_invite_link(CHANNEL_ID_2, member_limit=1).invite_link
                        set_user_received_link(user_id)
                        
                        markup = types.InlineKeyboardMarkup()
                        markup.add(types.InlineKeyboardButton("join channel 1", url=invite_link_1))
                        markup.add(types.InlineKeyboardButton("join channel 2", url=invite_link_2))
                        
                        bot.send_message(user_id, 'Click the buttons below to join the channels', reply_markup=markup)
                    else:
                        bot.send_message(user_id, 'You already got the link')
                    return

            new_markup = create_number_markup()
            bot.edit_message_caption(caption=f'Caution captcha has 5 numbers! If you dont see all of them please click image. Pass Captcha \n {new_message}', chat_id=user_id, message_id=call.message.message_id, reply_markup=new_markup)
        
        except ValueError:
            bot.answer_callback_query(call.id, 'wrong number')
        
    elif action == 'change':
        new_numbers = generate_random_numbers()
        image_path = create_image_with_numbers(new_numbers)
        with open(image_path, 'rb') as image_file:
            msg = bot.send_photo(user_id, image_file, caption='Caution captcha has 5 numbers! If you dont see all of them please click image. Pass Captcha')

        new_markup = create_number_markup()
        bot.edit_message_caption(caption='Caution captcha has 5 numbers! If you dont see all of them please click image. Pass Captcha', chat_id=user_id, message_id=msg.message_id, reply_markup=new_markup)
    
    elif action == 'delete':
        if user_data_entry['selected_numbers']:
            user_data_entry['selected_numbers'].pop()
            new_message = ' '.join(map(str, user_data_entry['selected_numbers']))

            correct_numbers = user_data_entry['random_numbers']

            if len(user_data_entry['selected_numbers']) == len(correct_numbers):
                if user_data_entry['selected_numbers'] == correct_numbers:
                    if not check_user(user_id):
                        invite_link_1 = bot.create_chat_invite_link(CHANNEL_ID_1, member_limit=1).invite_link
                        invite_link_2 = bot.create_chat_invite_link(CHANNEL_ID_2, member_limit=1).invite_link
                        set_user_received_link(user_id)
                        
                        markup = types.InlineKeyboardMarkup()
                        markup.add(types.InlineKeyboardButton("join channel 1", url=invite_link_1))
                        markup.add(types.InlineKeyboardButton("join channel 2", url=invite_link_2))
                        
                        bot.send_message(user_id, 'Click the buttons below to join the channels', reply_markup=markup)
                    else:
                        bot.send_message(user_id, 'You already got the link')
                    return

            new_markup = create_number_markup()
            bot.edit_message_caption(caption=f'Caution captcha has 5 numbers! If you dont see all of them please click image. Pass Captcha \n{new_message}', chat_id=user_id, message_id=call.message.message_id, reply_markup=new_markup)
        else:
            bot.send_message(user_id, 'There are no numbers to delete.')

init_db()
bot.polling()
