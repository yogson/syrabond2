from uuid import uuid4 as uuid
from time import sleep

from .common import log
from .mqttsender import Mqtt


class MessageHandler:

    def __init__(self):
        self.resources = {}
        self.loaded = False
        self.models = []

    def load_resources(self, models: list):
        if not self.loaded:
            log('Loading resources...')
            self.models = models
            self.update_resources()
            self.loaded = True

    def update_resources(self):
        log('Fetching resources from DB...')
        for model in self.models:
            qs = model.objects.exclude(uid__in=self.resources)
            for obj in qs:
                log(f'connecting {obj}')
                obj.connect()
                self.resources.update({obj.uid: obj})

    def handle(self, payload):
        _type, _id, channel, msg = payload

        resource = self.resources.get(_id)

        if resource:
            resource.refresh_from_db()
            resource.update_state(msg, channel)


class Comm:
    # 'to send': 'to store'
    command_map = {
        'off': 'off',
        'on': 'on'
    }


mqtt_sender = Mqtt('syrabond_sender_' + str(uuid()), clean_session=True)
sleep(0.01)
mqtt_listener = Mqtt('syrabond_automation_' + str(uuid()), clean_session=False, handler=MessageHandler())
