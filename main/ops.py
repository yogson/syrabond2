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
        for model in self.models:
            qs = model.objects.exclude(uid__in=self.resources)
            for obj in qs:
                log(f'connecting {obj}')
                obj.connect()
                self.resources.update({obj.uid: obj})

    def handle(self, topic=None, payload=None):
        resource = None
        topic_items = topic.split('/')

        for pos, item in enumerate(topic_items):
            if item in self.resources:
                resource = self.resources[item]
                break

        if resource:
            resource.refresh_from_db()
            if pos + 1 < len(topic_items):
                channel = '.'.join(topic_items[pos + 1:])
                resource.update_state(payload, channel)
            else:
                resource.update_state(payload)



class Comm:
    # 'to send': 'to store'
    command_map = {
        'off': 'off',
        'on': 'on'
    }


mqtt_sender = Mqtt('syrabond_sender_' + str(uuid()), clean_session=True)
sleep(0.01)
mqtt_listener = Mqtt('syrabond_automation_' + str(uuid()), clean_session=False, handler=MessageHandler())
