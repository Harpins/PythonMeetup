from django.core.management.base import BaseCommand
from events_bot.schedule import main

class Command(BaseCommand):
    help = 'Запускает schedule.py'

    def handle(self, *args, **options):
        main()