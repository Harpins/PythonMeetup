from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.error import TelegramError
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters
from events_bot.views import get_program, serialize_current_events, get_staff_ids, send_question
from environs import Env


def get_main_keyboard(is_manager=False, is_speaker=False):
    keyboard = [[InlineKeyboardButton("📅 Программа", callback_data='schedule'), InlineKeyboardButton(
        "❓ Задать вопрос", callback_data='ask_speaker')]]
    if is_manager:
        # Добавить кнопки для админа
        keyboard.append([InlineKeyboardButton(
            "Заглушка", callback_data='manager')])
    if is_speaker:
        # Добавить кнопки для спикера
        keyboard.append([InlineKeyboardButton(
            "Заглушка", callback_data='speaker')])
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


def get_confirm_question_keyboard():
    keyboard = [
        [InlineKeyboardButton("Подтвердить", callback_data='confirm_question'),
         InlineKeyboardButton("Отмена", callback_data='cancel_question')]
    ]
    return InlineKeyboardMarkup(keyboard)


def start(update: Update, context):
    staff_ids = get_staff_ids()
    manager_ids = staff_ids.get('manager_ids', [])
    speaker_ids = staff_ids.get('speaker_ids', [])
    is_manager = update.message.from_user.id in manager_ids
    is_speaker = update.message.from_user.id in speaker_ids
    context.user_data.update({
        'is_manager': is_manager,
        'is_speaker': is_speaker,
    })
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
    context.user_data['state'] = 'selecting_speaker'


def process_speaker_selection(update: Update, context):
    query = update.callback_query
    query.answer()

    if query.data == 'back':
        query.edit_message_text(
            "Выберите действие:",
            reply_markup=get_main_keyboard()
        )
        context.user_data.clear()
        return

    if query.data.startswith('ask_'):
        telegram_username = query.data.split('_', 1)[1]

        context.user_data.update({
            'state': 'awaiting_question',
            'telegram_username': telegram_username,
        })

        query.edit_message_text(
            "✍️ Введите ваш вопрос:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    "❌ Отмена", callback_data='cancel_question')]
            ])
        )
    else:
        query.edit_message_text(
            "Выберите действие:",
            reply_markup=get_main_keyboard()
        )
        context.user_data.clear()


def process_question(update: Update, context):
    if context.user_data.get('state') != 'awaiting_question':
        print(context.user_data.get('state'))
        return
    speaker_username = context.user_data.get('telegram_username')
    participant_id = update.message.from_user.id
    participant_name = update.message.from_user.first_name
    text = update.message.text
    try:
        context.user_data.update({
            'state': 'confirming_question',
            'question': {
                'speaker_username': speaker_username,
                'participant_id': participant_id,
                'participant_name': participant_name,
                'text': text
            }
        })
        keyboard = get_confirm_question_keyboard()
        if not keyboard:
            update.message.reply_text(
                "Ошибка при создании меню. Попробуйте позже.")
            return
        update.message.reply_text(
            f"Подтвердите ваш вопрос:\n\n{text}\n\nК спикеру: {speaker_username}",
            reply_markup=keyboard
        )

    except Exception as err:
        update.message.reply_text(
            f"Произошла ошибка {err}, попробуйте задать вопрос позже", reply_markup=get_main_keyboard())
        context.user_data['state'] = None
        context.user_data['telegram_username'] = None



def confirm_question(update: Update, context):
    query = update.callback_query
    query.answer()

    if context.user_data.get('state') != 'confirming_question':
        query.message.reply_text("Выберите действие:",
                                 reply_markup=get_main_keyboard())
        context.user_data.clear()
        return

    if query.data == 'confirm_question':
        question_data = context.user_data.get('question')
        if not question_data:
            query.message.reply_text(
                "Ошибка: данные вопроса отсутствуют.", reply_markup=get_main_keyboard())
            return
        try:
            send_question(
                speaker_username=question_data.get('speaker_username'),
                participant_id=question_data.get('participant_id'),
                participant_name=question_data.get('participant_name'),
                text=question_data.get('text')
            )
            query.message.reply_text(
                "Вопрос успешно отправлен", reply_markup=get_main_keyboard())
        except Exception as err:
            query.message.reply_text(
                f"Произошла ошибка {err}, попробуйте задать вопрос позже", reply_markup=get_main_keyboard())
            raise err
    elif query.data == 'cancel_question':
        query.message.reply_text(
            "Вопрос отменен.", reply_markup=get_main_keyboard())
    else:
        query.message.reply_text(
            "Что-то пошло не так", reply_markup=get_main_keyboard())

    context.user_data.clear()


def main():
    env = Env()
    env.read_env()
    tg_bot_token = env.str("TG_BOT_TOKEN")
    updater = Updater(tg_bot_token, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CallbackQueryHandler(schedule, pattern='schedule'))
    dp.add_handler(CallbackQueryHandler(ask_speaker, pattern='ask_speaker'))
    dp.add_handler(CallbackQueryHandler(
        process_speaker_selection, pattern='(ask_@[\w]+|back)'))
    dp.add_handler(MessageHandler(Filters.all, process_question))
    dp.add_handler(CallbackQueryHandler(confirm_question,
                   pattern='(confirm_question|cancel_question)'))
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
