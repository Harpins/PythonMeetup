from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from environs import Env
from .views import get_program, serialize_current_events


# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/schedule - Посмотреть программу\n"
        "/ask - Текущий доклад + вопросы спикеру\n"
        #"/network - Познакомиться с другими\n" Заглушка для других команд
        #"/donate - Поддержать мероприятие"
    )
    
# Команда /schedule
async def schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    response = "Программа PythonMeetup на сегодня:\n"
    await update.message.reply_text(response)

    
# Команда /ask 
async def current_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    response = "Текущие спикеры:"
    await update.message.reply_text(response)

def main():
    env = Env()
    env.read_env()
    tg_bot_token = env.str("TG_BOT_TOKEN")
    app = Application.builder().token(tg_bot_token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("schedule", schedule))
    app.add_handler(CommandHandler("ask", current_event))

    app.run_polling()


if __name__ == '__main__':
    main()
    