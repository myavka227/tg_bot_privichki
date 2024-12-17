import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime
import os
import json

# Токен для Телеграм-бота
API_TOKEN = '8136774944:AAF9HhHax42vnA6ucdpCArAuuRtVyoP9BWs'

bot = telebot.TeleBot(API_TOKEN)

# Пути для хранения данных
HABIT_DATA_PATH = "habits.json"
TASK_DATA_PATH = "tasks.json"
LOG_FILE = "bot_log.txt"

# Базовый класс для трекеров
class BaseTracker:
    def __init__(self, data_path):
        self.data_path = data_path
        self.data = {}
        self.load_data()

    def load_data(self):
        if os.path.exists(self.data_path):
            with open(self.data_path, "r") as file:
                self.data = json.load(file)
        else:
            self.data = {}

    def save_data(self):
        with open(self.data_path, "w") as file:
            json.dump(self.data, file, indent=4)

    def add_entry(self, user_id, entry):
        if user_id not in self.data:
            self.data[user_id] = []
        self.data[user_id].append(entry)
        self.save_data()

    def get_entries(self, user_id):
        return self.data.get(user_id, [])

    def delete_entry(self, user_id, index):
        if user_id in self.data and 0 <= index < len(self.data[user_id]):
            del self.data[user_id][index]
            self.save_data()

# Дочерние классы
class HabitTracker(BaseTracker):
    def __init__(self):
        super().__init__(HABIT_DATA_PATH)

class TaskTracker(BaseTracker):
    def __init__(self):
        super().__init__(TASK_DATA_PATH)

# Инициализация трекеров
habit_tracker = HabitTracker()
task_tracker = TaskTracker()

# Состояния пользователей
user_states = {}

def set_user_state(user_id, state):
    user_states[user_id] = state

def get_user_state(user_id):
    return user_states.get(user_id)

def reset_user_state(user_id):
    user_states.pop(user_id, None)

# Отправка файла со списком привычек
def send_habit_file(chat_id, habits):
    file_path = f"habits_{chat_id}.txt"  # Уникальный файл для пользователя
    with open(file_path, "w", encoding="utf-8") as file:
        file.write("Ваши привычки:\n")
        for i, habit in enumerate(habits, start=1):
            file.write(f"{i}. {habit}\n")
    with open(file_path, "rb") as file:
        bot.send_document(chat_id, file)
    os.remove(file_path)  # Удаляем файл после отправки

# Главное меню
def main_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Добавить привычку", "Удалить привычку")
    markup.add("Добавить задание на день", "Чек-лист на день")
    markup.add("Добавить нотификатор", "Список привычек")
    return markup

# Обработчик команды /start
@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(message.chat.id, "👋 Привет! Я помогу тебе сформировать полезные привычки.", reply_markup=main_menu())

# Добавление привычки
@bot.message_handler(func=lambda message: message.text == "Добавить привычку")
def add_habit(message):
    set_user_state(message.chat.id, "adding_habit")
    bot.send_message(message.chat.id, "Введите название привычки:")

@bot.message_handler(func=lambda message: get_user_state(message.chat.id) == "adding_habit")
def process_habit(message):
    habit_name = message.text
    habit_tracker.add_entry(str(message.chat.id), habit_name)
    reset_user_state(message.chat.id)
    bot.send_message(message.chat.id, f"✅ Привычка '{habit_name}' добавлена!", reply_markup=main_menu())

# Удаление привычки
@bot.message_handler(func=lambda message: message.text == "Удалить привычку")
def delete_habit(message):
    habits = habit_tracker.get_entries(str(message.chat.id))
    if not habits:
        bot.send_message(message.chat.id, "😔 У вас нет привычек для удаления.", reply_markup=main_menu())
    else:
        set_user_state(message.chat.id, "deleting_habit")
        response = "📋 Ваши привычки:\n" + "\n".join([f"{i+1}. {habit}" for i, habit in enumerate(habits)])
        response += "\n\nВведите номер привычки для удаления:"
        bot.send_message(message.chat.id, response)

@bot.message_handler(func=lambda message: get_user_state(message.chat.id) == "deleting_habit")
def process_delete_habit(message):
    try:
        index = int(message.text) - 1
        habits = habit_tracker.get_entries(str(message.chat.id))
        if 0 <= index < len(habits):
            deleted_habit = habits[index]
            habit_tracker.delete_entry(str(message.chat.id), index)
            bot.send_message(message.chat.id, f"✅ Привычка '{deleted_habit}' удалена!", reply_markup=main_menu())
        else:
            bot.send_message(message.chat.id, "❌ Неверный номер. Попробуйте снова.")
    except ValueError:
        bot.send_message(message.chat.id, "❌ Пожалуйста, введите номер привычки.")
    reset_user_state(message.chat.id)

@bot.message_handler(func=lambda message: message.text == "Чек-лист на день")
def checklist(message):
    tasks = task_tracker.get_entries(str(message.chat.id))
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔄 Обновить", callback_data="refresh_tasks"))
    
    if tasks:
        response = "📋 Ваш чек-лист на день:\n" + "\n".join([f"{i+1}. {task}" for i, task in enumerate(tasks)])
    else:
        response = "😔 Чек-лист на день пуст."
    bot.send_message(message.chat.id, response, reply_markup=markup)

# Добавление задания на день
@bot.message_handler(func=lambda message: message.text == "Добавить задание на день")
def add_task(message):
    set_user_state(message.chat.id, "adding_task")
    bot.send_message(message.chat.id, "Введите задание на день:")

@bot.message_handler(func=lambda message: get_user_state(message.chat.id) == "adding_task")
def process_task(message):
    task = message.text
    task_tracker.add_entry(str(message.chat.id), task)
    reset_user_state(message.chat.id)
    bot.send_message(message.chat.id, f"✅ Задание '{task}' добавлено в чек-лист на день!", reply_markup=main_menu())

# Чек-лист на день
@bot.message_handler(func=lambda message: message.text == "Чек-лист на день")
def checklist(message):
    tasks = task_tracker.get_entries(str(message.chat.id))
    if tasks:
        response = "📋 Ваш чек-лист на день:\n" + "\n".join([f"{i+1}. {task}" for i, task in enumerate(tasks)])
    else:
        response = "😔 Чек-лист на день пуст."
    bot.send_message(message.chat.id, response)

# Добавление нотификатора
@bot.message_handler(func=lambda message: message.text == "Добавить нотификатор")
def add_notifier(message):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("✅ ОК", callback_data="notifier_ok"),
               InlineKeyboardButton("↩️ Вернуться", callback_data="notifier_back"))
    bot.send_message(message.chat.id, 
                     "🕒 Напишите сообщение, зажмите кнопку 'Отправить позже' и назначьте время для нотификатора.\nКогда будет выполнено, нажмите 'ОК'.", 
                     reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("notifier_"))
def handle_notifier_buttons(call):
    if call.data == "notifier_ok":
        bot.send_message(call.message.chat.id, "✅ Нотификатор добавлен!", reply_markup=main_menu())
    elif call.data == "notifier_back":
        bot.send_message(call.message.chat.id, "↩️ Возвращаемся в главное меню.", reply_markup=main_menu())

@bot.callback_query_handler(func=lambda call: call.data == "refresh_tasks")
def refresh_tasks(call):
    task_tracker.data[str(call.message.chat.id)] = []  # Очистка списка задач пользователя
    task_tracker.save_data()  # Сохранение изменений
    bot.edit_message_text("✅ Чек-лист на день был обновлён и теперь пуст.", 
                          chat_id=call.message.chat.id, 
                          message_id=call.message.message_id, 
                          reply_markup=None)

# Список привычек
@bot.message_handler(func=lambda message: message.text == "Список привычек")
def list_habits(message):
    habits = habit_tracker.get_entries(str(message.chat.id))
    if habits:
        response = "📋 Ваши привычки:\n" + "\n".join([f"{i+1}. {habit}" for i, habit in enumerate(habits)])
        bot.send_message(message.chat.id, response)
        send_habit_file(message.chat.id, habits)  # Отправка файла
    else:
        response = "😔 У вас пока нет привычек."
        bot.send_message(message.chat.id, response)

# Обработчик неизвестных команд
@bot.message_handler(func=lambda message: True)
def unknown_command(message):
    bot.send_message(message.chat.id, "❌ Неизвестная команда. Пожалуйста, выберите действие из меню.", reply_markup=main_menu())

# Запуск бота
bot.polling(none_stop=True)
