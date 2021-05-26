from datetime import datetime, timedelta, timezone


class Clock:

    def __init__(self, **kwargs):
        pass

    def __call__(self, *args, **kwargs):
        return self.state()

    def state(self):
        offset = timedelta(hours=3)
        tz = timezone(offset, name='МСК')
        return {'state': datetime.now(tz=tz).strftime('%H:%M')}


class Weather:

    def __init__(self, **kwargs):
        pass

    def __call__(self, *args, **kwargs):
        return {'state': '0'}


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
