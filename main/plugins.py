from datetime import datetime, timedelta, timezone
import requests

from django.utils import datetime_safe


class Clock:

    def __init__(self, **kwargs):
        pass

    def __call__(self, *args, **kwargs):
        return self.state()

    def state(self):
        offset = timedelta(hours=3)
        tz = timezone(offset, name='МСК')
        return datetime.now(tz=tz).strftime('%H:%M')


class Weather:

    link = "http://api.openweathermap.org/data/2.5/weather?q=Onufriyevo&appid=1c5aecfe6332dd9e8de93ad5c949000f"

    def __init__(self, **kwargs):
        self.data = None

    def __call__(self, *args, **kwargs):
        updated_at = kwargs.get('service', {}).get('updated_at', 0)
        if updated_at + timedelta(minutes=10).total_seconds() < datetime.now().timestamp():
            self.refresh()
        return self.data

    def refresh(self):
        self.data = self.update_data()
        self.data.update({'daylight': self.get_daylight()})
        self.data.update({'service': {'updated_at': datetime.now().timestamp()}})

    def get_daylight(self):
        sunrise_time = datetime.strptime(self.data.get('sunrise', '06:00'), '%H:%M')
        sunrise_today = datetime_safe.datetime.now().replace(
            hour=sunrise_time.hour, minute=sunrise_time.minute, second=0, microsecond=0)
        sunset_time = datetime.strptime(self.data.get('sunset', '19:00'), '%H:%M')
        sunset_today = datetime_safe.datetime.now().replace(
            hour=sunset_time.hour, minute=sunset_time.minute, second=0, microsecond=0)

        return sunset_today > datetime.now() > sunrise_today

    def update_data(self):
        try:
            data = self.get_data()
        except:
            return {}
        return {
            'sunrise': datetime.fromtimestamp(data.get('sys', {}).get('sunrise', 0)).time().strftime('%H:%M'),
            'sunset': datetime.fromtimestamp(data.get('sys', {}).get('sunset', 0)).time().strftime('%H:%M'),
            'current_temp': round(data.get('main', {}).get('temp', 273.15) - 273.15, 1),
        }

    def get_data(self):
        return requests.get(self.link).json()


class Timer:

    def __init__(self, **kwargs):
        settings = kwargs.get('settings', {})
        state = kwargs.get('state', {}).get('timing', {})
        self.working_time = settings.get('working time')
        self.sleeping_time = settings.get('sleeping time')
        self.to_stop = datetime.fromtimestamp(state.get('to_stop')) if state.get('to_stop') else None
        self.to_start = datetime.fromtimestamp(state.get('to_start')) if state.get('to_start') else None

    @property
    def sleeping(self):
        return timedelta(seconds=self.sleeping_time)

    @property
    def working(self):
        return timedelta(seconds=self.working_time)

    def __call__(self, *args, **kwargs):
        now = datetime.now()
        if not self.to_start:
            self.to_start = now
        if not self.to_stop:
            self.to_stop = self.to_start + self.working

        if self.to_stop <= now:
            self.to_start = now + self.sleeping
            self.to_stop = self.to_start + self.working

        return {
            'state': now >= self.to_start,
            'timing': {
                'to_stop': self.to_stop.timestamp(), 'to_start': self.to_start.timestamp()
            }

        }
