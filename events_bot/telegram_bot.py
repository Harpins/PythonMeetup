from telegram.ext import (
    Updater,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    Filters,
    ConversationHandler
)
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from django.conf import settings
from events_bot.models import Event, Participant, Donation
from yookassa import Payment, Configuration
import uuid

CHOOSE_CUSTOM_AMOUNT = range(1)

# Инициализация ЮKassa
Configuration.account_id = settings.YOOKASSA_SHOP_ID
Configuration.secret_key = settings.YOOKASSA_SECRET_KEY


def start(update, context):
    user = update.message.from_user
    Participant.objects.get_or_create(
        telegram_id=user.id,
        defaults={
            'telegram_username': user.username,
            'name': user.first_name or 'Аноним'
        }
    )

    event = Event.objects.filter(is_active=True).first()
    event_name = event.title if event else "Python Meetup"

    update.message.reply_text(
        f"Привет! Я бот для {event_name}\n\n"
        "Доступные команды:\n"
        "/start - начало работы\n"
        "/program - программа мероприятия\n"
        "/donate - поддержать мероприятие"
    )


def program(update, context):
    event = Event.objects.filter(is_active=True).first()
    if event:
        update.message.reply_text(event.get_program())
    else:
        update.message.reply_text("Сейчас нет активных мероприятий")


def donate(update, context):
    if not Event.objects.filter(is_active=True).exists():
        update.message.reply_text("Сейчас нет активных мероприятий для доната")
        return

    keyboard = [
        [InlineKeyboardButton("100 ₽", callback_data='donate_100')],
        [InlineKeyboardButton("300 ₽", callback_data='donate_300')],
        [InlineKeyboardButton("500 ₽", callback_data='donate_500')],
        [InlineKeyboardButton("Другая сумма", callback_data='donate_custom')],
    ]
    update.message.reply_text(
        "Выберите сумму доната:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


def handle_fixed_donate_callback(update, context):
    query = update.callback_query
    query.answer()

    if not Event.objects.filter(is_active=True).exists():
        query.edit_message_text("Сейчас нет активных мероприятий для доната")
        return ConversationHandler.END

    try:
        amount = int(query.data.split('_')[1])
        create_payment(update, context, amount)
    except (IndexError, ValueError):
        query.edit_message_text("Ошибка при обработке суммы.")
    return ConversationHandler.END


def handle_custom_donate_callback(update, context):
    query = update.callback_query
    query.answer()

    if not Event.objects.filter(is_active=True).exists():
        query.edit_message_text("Сейчас нет активных мероприятий для доната")
        return ConversationHandler.END

    query.edit_message_text("Введите сумму доната в рублях (от 10 до 15000):")
    return CHOOSE_CUSTOM_AMOUNT


def handle_custom_amount(update, context):
    try:
        amount = int(update.message.text.strip())
        if amount < 10 or amount > 15000:
            update.message.reply_text("Сумма должна быть от 10 до 15000 ₽. Пожалуйста, введите корректную сумму:")
            return CHOOSE_CUSTOM_AMOUNT

        create_payment(update, context, amount)
        return ConversationHandler.END

    except ValueError:
        update.message.reply_text("Пожалуйста, введите число (например: 250):")
        return CHOOSE_CUSTOM_AMOUNT


def cancel(update, context):
    update.message.reply_text("Донат отменён.")
    return ConversationHandler.END


def create_payment(update, context, amount):
    # Определяем откуда пришел update (из сообщения или callback)
    if update.callback_query:
        user = update.callback_query.from_user
        chat_id = update.callback_query.message.chat_id
    else:
        user = update.message.from_user
        chat_id = update.message.chat_id

    event = Event.objects.filter(is_active=True).first()
    if not event:
        error_msg = "Сейчас нет активных мероприятий для доната"
        if update.callback_query:
            update.callback_query.edit_message_text(error_msg)
        else:
            update.message.reply_text(error_msg)
        return

    participant, _ = Participant.objects.get_or_create(
        telegram_id=user.id,
        defaults={
            'telegram_username': user.username,
            'name': user.first_name or 'Аноним'
        }
    )

    try:
        payment = Payment.create({
            "amount": {"value": str(amount), "currency": "RUB"},
            "confirmation": {
                "type": "redirect",
                "return_url": f"https://t.me/{settings.TG_BOT_USERNAME}"
            },
            "description": f"Донат на {event.title}",
            "metadata": {
                "user_id": user.id,
                "event_id": event.id
            }
        }, str(uuid.uuid4()))

        Donation.objects.create(
            event=event,
            participant=participant,
            amount=amount,
            payment_id=payment.id,
            is_confirmed=True
        )

        reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton(
            "💳 Оплатить",
            url=payment.confirmation.confirmation_url
        )]])

        message = f"Ссылка для оплаты {amount}₽:"
        if update.callback_query:
            update.callback_query.edit_message_text(message, reply_markup=reply_markup)
        else:
            context.bot.send_message(chat_id, message, reply_markup=reply_markup)

        event = Event.objects.filter(is_active=True).first()
        event_name = event.title if event else "Python Meetup"

        context.bot.send_message(
            chat_id=chat_id,
            text=f"✨<b>Благодарим за поддержку {event_name}!</b>\n\n"
                 f"Твой донат {amount}₽ — это:\n"
                 f"• ☕ 10 чашек кофе для спикеров\n"
                 f"• 📚 Новые материалы для участников\n"
                 f"• 💻 Лучшее оборудование для трансляций\n\n"
                 f"<i>Спасибо за вклад в развитие комьюнити!</i>",
            parse_mode='HTML'
        )

    except Exception as e:
        error_msg = f"Ошибка при создании платежа: {str(e)}"
        if update.callback_query:
            update.callback_query.edit_message_text(error_msg)
        else:
            context.bot.send_message(chat_id, error_msg)


def setup_dispatcher(dp):
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("program", program))
    dp.add_handler(CommandHandler("donate", donate))

    dp.add_handler(CallbackQueryHandler(handle_fixed_donate_callback, pattern='^donate_\\d+$'))

    donate_conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(handle_custom_donate_callback, pattern='^donate_custom$')
        ],
        states={
            CHOOSE_CUSTOM_AMOUNT: [
                MessageHandler(Filters.text & ~Filters.command, handle_custom_amount)
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    dp.add_handler(donate_conv_handler)

    return dp


def start_bot():
    updater = Updater(settings.TG_BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp = setup_dispatcher(dp)

    updater.start_polling()
    updater.idle()
