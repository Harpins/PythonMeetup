from django.utils import timezone
from .models import Event, Speaker, TimeSlot, Participant

def get_program():
    today = timezone.now().date()
    today_events = Event.objects.filter(date=today).prefetch_related('speakers', 'time_slots').order_by('time_slots__start_time')
    program = []
    for event in today_events:
        for timeslot in event.time_slots.all():
            speaker = timeslot.speaker.name
            program.append(
                f"{timeslot.start_time.strftime('%H:%M')} - {timeslot.end_time.strftime('%H:%M')}: "
                f"{timeslot.title} ({', '.join(speaker)})"
            )
    return program

def serialize_current_events():
    now = timezone.now()
    current_timeslots = TimeSlot.objects.filter(
        start_time__lte=now, end_time__gte=now
    ).prefetch_related('event__speakers', 'speaker').order_by('start_time')
    events_info = []
    speakers_list = []
    for timeslot in current_timeslots:
        speaker = timeslot.speaker
        speakers_list.append(speaker)
        events_info.append(
            f"{timeslot.start_time.strftime('%H:%M')} - {timeslot.end_time.strftime('%H:%M')}: "
            f"{speaker.name} - {timeslot.event.title}"
        )
    return {
        'events': events_info,
        'speakers': speakers_list,
    }

def get_manager_ids():
    managers = Participant.objects.filter(is_event_manager=True)
    return [str(manager.telegram_id) for manager in managers]