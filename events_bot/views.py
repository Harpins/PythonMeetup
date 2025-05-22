from django.shortcuts import render
from django.utils import timezone
from .models import Event, Participant


def get_program():
    today = timezone.now().date()
    today_events = Event.objects.filter(date__date=today).prefetch_related(
        'speakers', 'time_slots',).order_by('time_slots')
    program = []
    for event in today_events:
        today_speakers = [speaker for speaker in event.speakers]
        program.append(
            f"{event.timeslots.start_time.strftime('%H:%M')} - {event.timeslots.end_time.strftime('%H:%M')}: "
            f"{event.title} ({today_speakers})"
        )
    return program


def serialize_current_events():
    now = timezone.now()
    current_events = Event.objects.prefetch_related('speakers', 'time_slots').filter(
        is_active=True, time_slots__start_time__lte=now, time_slots__end_time__gte=now).order_by('time_slots')
    current_speakers = []
    events_info = []
    for event in current_events:
        event_speakers = [speaker for speaker in event.speakers]
        current_speakers.append(event_speakers)
        events_info.append(
            f'{event.time_slots.start_time}:{event.time_slots.start_time} {event_speakers} {event.title}')
    return {
        'current_events': events_info,
        'current_speakers': current_speakers,
    }


def get_managers():
    return Participant.objects.filter(is_event_manager=True)