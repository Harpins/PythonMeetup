from django.core.management.base import BaseCommand
from events_bot.telegram_bot import start_bot  

class Command(BaseCommand):
    help = 'Запускает Telegram-бота для мероприятий'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Запуск Telegram-бота...'))
        try:
            start_bot()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Ошибка при запуске бота: {str(e)}'))