from django.conf import settings
from django.utils import timezone
from django.db import transaction, models
from .models import Speaker, Participant, Question
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from environs import Env


env = Env()
env.read_env()
BOT_TOKEN = settings.TG_BOT_TOKEN


def send_question(speaker_username, participant_id, participant_name, text):
    bot = Bot(token=BOT_TOKEN)

    try:
        with transaction.atomic():
            # Ищем спикера ТОЛЬКО по telegram_username
            speaker = Speaker.objects.get(telegram_username=speaker_username)

            # Проверяем, что спикер привязан к активному мероприятию
            if not speaker.events.filter(is_active=True).exists():
                raise Exception("Спикер не привязан к активному мероприятию")

            participant, _ = Participant.objects.get_or_create(
                telegram_id=participant_id,
                defaults={'name': participant_name}
            )
            event = speaker.events.filter(is_active=True).first()

            # Создаем вопрос в БД
            question = Question.objects.create(
                event=event,
                speaker=speaker,
                participant=participant,
                text=text
            )

            reply_markup = InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    "✅ Ответить", callback_data=f'answer_{question.id}')]
            ])

            bot.send_message(
                chat_id=speaker.telegram_id,
                text=f"❓ Новый вопрос от {participant_name}:\n\n{text}",
                reply_markup=reply_markup
            )

            return True

    except Speaker.DoesNotExist:
        raise Exception(f"Спикер @{speaker_username} не найден")
    except Exception as e:
        raise Exception(f"Ошибка при отправке вопроса: {str(e)}")
