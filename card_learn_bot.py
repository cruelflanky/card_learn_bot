import asyncio
import logging
import sqlite3
import datetime
import calendar
import random
import string
from time import time

from aiogram import types
from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage

API_TOKEN = ''
DELAY = 60
# Configure logging
logging.basicConfig(level=logging.INFO)
# Initialize bot and dispatcher
db = sqlite3.connect('database.db')
sql = db.cursor()
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

class WordFunc(StatesGroup):
	add_new_word = State()
	check_word = State()
	delete_word = State()

def get_random_string(length):
	letters = string.ascii_letters
	result_str = ''.join(random.choice(letters) for i in range(length))
	return result_str

@dp.message_handler(commands="delete", state="*")
async def delete_word_db_1(message: types.Message):
	await message.answer('Введите слово и его перевод через пробел,\nкоторое хотите удалить:\nword translation')
	await WordFunc.delete_word.set()

@dp.message_handler(state=WordFunc.delete_word, content_types=types.ContentTypes.TEXT)
async def delete_word_db_2(message: types.Message, state: FSMContext):
	try:
		chat_id = message.chat.id
		word, translate = message.text.lower().split()
		sql.execute("""
				DELETE FROM users
				WHERE chat_id = ? AND word = ? AND translate = ?;
					""", (chat_id, word, translate))
		db.commit()
		await message.reply('Запись была удалена в базе данных')
	except Exception as c:
		await message.answer('Что-то пошло не так, попробуйте еще раз /delete')
		await bot.send_message(364139276, 'Error: {}'.format(c))

	await state.finish()

@dp.message_handler(commands="new", state="*")
async def add_word_step_1(message: types.Message):
	await message.answer('Введите слово и его перевод через пробел:\nword translation')
	await WordFunc.add_new_word.set()

@dp.message_handler(state=WordFunc.add_new_word, content_types=types.ContentTypes.TEXT)
async def add_word_step_2(message: types.Message, state: FSMContext):
	try:
		now = datetime.datetime.now()
		chat_id = message.chat.id
		name = message.chat.username
		word, translate = message.text.lower().split()
		date_create = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
		date_1_return = (now + datetime.timedelta(days=2)).strftime("%Y-%m-%d %H:%M")
		date_2_return = (now + datetime.timedelta(weeks=1)).strftime("%Y-%m-%d %H:%M")
		date_3_return = (now + datetime.timedelta(weeks=2)).strftime("%Y-%m-%d %H:%M")
		sql.execute("INSERT INTO users VALUES (?,?,?,?,?,?,?,?)",
			(chat_id, name, word, translate, date_create, date_1_return, date_2_return, date_3_return))
		db.commit()
		await message.reply('Новое запись добавлена:')
		await message.answer('Cлово - {} | Перевод - {}'.format(word, translate))

	except Exception as c:
		await message.answer('Что-то пошло не так, попробуйте еще раз /new')
		await bot.send_message(364139276, 'Error: {}'.format(c))

	await state.finish()

async def right_answer_db_update(chat_id, word, translate):
	sql.execute("""
				SELECT date_1_return, date_2_return, date_3_return FROM users
				WHERE chat_id = ? AND word = ? AND translate = ?;
					""", (chat_id, word, translate))
	row = sql.fetchone()
	if row[0]:
		sql.execute('UPDATE users SET date_1_return = NULL ' \
			'WHERE chat_id = ? AND word = ? AND translate = ?;', (chat_id, word, translate))
	elif row[1]:
		sql.execute('UPDATE users SET date_2_return = NULL ' \
			'WHERE chat_id = ? AND word = ? AND translate = ?;', (chat_id, word, translate))
	elif row[2]:
		sql.execute('UPDATE users SET date_3_return = NULL ' \
			'WHERE chat_id = ? AND word = ? AND translate = ?;', (chat_id, word, translate))
	db.commit()

async def update_date_db(chat_id, word, translate):
	now = datetime.datetime.now()
	sql.execute("""
				SELECT date_1_return, date_2_return, date_3_return FROM users
				WHERE chat_id = ? AND word = ? AND translate = ?;
					""", (chat_id, word, translate))
	row = sql.fetchone()
	date_1 = (now + datetime.timedelta(days=2)).strftime("%Y-%m-%d %H:%M")
	date_2 = (now + datetime.timedelta(weeks=1)).strftime("%Y-%m-%d %H:%M")
	date_3 = (now + datetime.timedelta(weeks=2)).strftime("%Y-%m-%d %H:%M")
	sql.execute('UPDATE users SET date_1_return = ?, date_2_return = ?, date_3_return = ? ' \
			'WHERE chat_id = ? AND word = ? AND translate = ?;', (date_1, date_2, date_3, chat_id, word, translate))
	db.commit()

@dp.message_handler(state=WordFunc.check_word, content_types=types.ContentTypes.TEXT)
async def check_translation(message: types.Message, state: FSMContext):
	sql.execute("""
				SELECT word FROM users
				WHERE chat_id = ? AND translate = ?;
					""", (message.chat.id, message.text.lower()))
	word = sql.fetchone()
	try:
		if word:
			translate = message.text.lower()
			await right_answer_db_update(message.chat.id, word[0], translate)
			await message.reply('Перевод верен!')
		else:
			sql.execute('SELECT word, translate FROM buffer WHERE chat_id = ?;', (message.chat.id, ))
			buf = sql.fetchone()
			word = buf[0]
			translate = buf[1]
			await update_date_db(message.chat.id, word, translate)
			await message.reply('Неверный перевод!')
			await message.answer('Даты повторной проверки обновлены')
			sql.execute('DELETE FROM buffer WHERE chat_id = ?;', (message.chat.id, ))
			db.commit()

	except Exception as c:
		await message.answer('Что-то пошло не так, свяжитесь с создателем')
		await bot.send_message(364139276, 'Error: {}'.format(c))

	await state.finish()

@dp.message_handler(commands=['list'])
async def help_message(message: types.Message):
	sql.execute("""
					SELECT chat_id, word, translate, date_create FROM users
					WHERE chat_id = ?;
						""",(message.chat.id,))
	rows = sql.fetchall()
	msg = ''
	for row in rows:
		msg = msg + row[3] + ' | ' + row[1] + ' : ' + row[2] + '\n'
	await message.answer('Список всех ваших слов:\n' + msg)

@dp.message_handler(commands=['test'])
async def test_message(message: types.Message):
	word = get_random_string(5).lower()
	translate = get_random_string(5).lower()
	now = datetime.datetime.now()
	chat_id = message.chat.id
	name = message.chat.username
	date_create = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
	date_1_return = now.strftime("%Y-%m-%d %H:%M")
	date_2_return = (now + datetime.timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M")
	date_3_return = (now + datetime.timedelta(minutes=2)).strftime("%Y-%m-%d %H:%M")
	sql.execute("INSERT INTO users VALUES (?,?,?,?,?,?,?,?)",
		(chat_id, name, word, translate, date_create, date_1_return, date_2_return, date_3_return))
	db.commit()
	await message.reply('Новое запись добавлена:')
	await message.answer('Cлово - {} | Перевод - {}'.format(word, translate))
	await message.answer("""Дата 1 - {}\n
							Дата 2 - {}\n
							Дата 3 - {}\n""".format(date_1_return,date_2_return, date_3_return))

@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
	await message.answer('🤖 Команды бота 🤖'
		+ '\n🐱 /start , /help - знакомство с ботом'
		+ '\n📓 /new - записать новое слово'
		+ '\n🗄 /list - увидеть список своих слов'
		+ '\n🙅🏼‍♀️ /delete - удалить карточку')

async def send_card(chat_id, word, translate, state):
	sql.execute("INSERT INTO buffer VALUES (?,?,?)", (chat_id, word, translate))
	db.commit()
	await bot.send_message(chat_id, 'Напишите перевод слова ' + word)
	await state.set_state(WordFunc.check_word)

async def check_queue():
	now = datetime.datetime.now()
	sql.execute("""
	SELECT chat_id, word, translate FROM queue
					""")
	row = sql.fetchone()
	if row:
		state = dp.current_state(user=row[0], chat=row[0])
		current_state = await state.get_state()
		if current_state is None:
			await bot.send_message(row[0], 'Напишите перевод слова ' + row[1])
			await state.set_state(WordFunc.check_word)
			sql.execute("""
					DELETE FROM queue
					WHERE chat_id = ? AND word = ? AND translate = ?;
						""", (row[0], row[1], row[2]))
			db.commit()


async def check_db(*args):
	now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
	sql.execute("""
	SELECT chat_id, word, translate, date_1_return, date_2_return, date_3_return FROM users
				""")
	rows = sql.fetchall()
	await check_queue()
	for row in rows:
		state = dp.current_state(user=row[0], chat=row[0])
		current_state = await state.get_state()
		if row[3] == now:
			if current_state is not None:
				sql.execute("INSERT INTO queue VALUES (?,?,?)", (row[0], row[1], row[2]))
			else:
				await send_card(row[0], row[1], row[2], state)
		elif row[4] == now:
			if current_state is not None:
				sql.execute("INSERT INTO queue VALUES (?,?,?)", (row[0], row[1], row[2]))
			else:
				await send_card(row[0], row[1], row[2], state)
		elif row[5] == now:
			if current_state is not None:
				sql.execute("INSERT INTO queue VALUES (?,?,?)", (row[0], row[1], row[2]))
			else:
				await send_card(row[0], row[1], row[2], state)
		db.commit()


def repeat(coro, loop):
	asyncio.ensure_future(coro(), loop=loop)
	loop.call_later(DELAY, repeat, coro, loop)


if __name__ == '__main__':
	sql.execute("""CREATE TABLE IF NOT EXISTS users (
	chat_id TEXT,
	name TEXT,
	word TEXT,
	translate TEXT,
	date_create TEXT,
	date_1_return TEXT,
	date_2_return TEXT,
	date_3_return TEXT
	)""")
	sql.execute("""CREATE TABLE IF NOT EXISTS queue (
	chat_id TEXT,
	word TEXT,
	translate TEXT
	)""")
	sql.execute("""CREATE TABLE IF NOT EXISTS buffer (
	chat_id TEXT,
	word TEXT,
	translate TEXT
	)""")
	db.commit()
	loop = asyncio.get_event_loop()
	loop.call_later(DELAY, repeat, check_db, loop)
	executor.start_polling(dp, loop=loop)
