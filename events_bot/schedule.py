from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, ContextTypes
from environs import Env
from events_bot.views import get_program, serialize_current_events, get_manager_ids


def get_main_keyboard(is_manager=False):
    keyboard = [[InlineKeyboardButton("📅 Программа", callback_data='schedule'), InlineKeyboardButton(
        "❓ Задать вопрос", callback_data='ask_speaker')]]
    if is_manager:
        keyboard.append([InlineKeyboardButton("Заглушка", callback_data='manager')])  # Добавить кнопки для админа
    return InlineKeyboardMarkup(keyboard)


def get_ask_speaker_keyboard(speakers):
    keyboard = [[InlineKeyboardButton("Назад", callback_data='back')]]
    for speaker in speakers:
        if speaker.telegram_username:
            keyboard.append([InlineKeyboardButton(
                speaker.name, callback_data=f"ask_{speaker.telegram_username}")])
        else:
            continue
    return InlineKeyboardMarkup(keyboard)


def start(update: Update, context):
    manager_ids = get_manager_ids()
    is_manager = str(update.message.from_user.id) in manager_ids
    update.message.reply_text(
        "Привет! Я бот PythonMeetup. Выбери действие:",
        reply_markup=get_main_keyboard(is_manager)
    )


def schedule(update: Update, context):
    query = update.callback_query
    query.answer()
    program = get_program()
    if not program:
        query.message.reply_text(
            "Программа пока пуста.", reply_markup=get_main_keyboard())
        return
    response = "Программа PythonMeetup:\n"
    for event in program:
        response += event
    query.message.reply_text(response, reply_markup=get_main_keyboard())


def ask_speaker(update: Update, context):
    query = update.callback_query
    query.answer()
    raw_info = serialize_current_events()
    current_events = raw_info.get("events")
    if not current_events:
        query.message.reply_text(
            "Сейчас нет активных докладов.", reply_markup=get_main_keyboard())
        return
    response = "Активные доклады:\n"
    for event in current_events:
        response += f"{event}\n"
    response += "Выберите докладчика для вопросов:\n"     
    current_speakers = raw_info.get("speakers")
    query.message.reply_text(
            response, reply_markup=get_ask_speaker_keyboard(current_speakers))
    return
    
def main():
    env = Env()
    env.read_env()
    tg_bot_token = env.str("TG_BOT_TOKEN")
    updater = Updater(tg_bot_token, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CallbackQueryHandler(schedule, pattern="schedule"))
    dp.add_handler(CallbackQueryHandler(ask_speaker, pattern="ask_speaker"))
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
