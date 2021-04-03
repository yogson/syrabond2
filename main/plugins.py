from datetime import datetime, timedelta, timezone


class Clock:

    def __call__(self, *args, **kwargs):
        return self.state()

    def state(self):
        offset = timedelta(hours=3)
        tz = timezone(offset, name='МСК')
        return datetime.now(tz=tz).strftime('%H:%M')


class Weather:

    def __call__(self, *args, **kwargs):
        return '0'