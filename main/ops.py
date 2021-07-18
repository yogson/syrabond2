from uuid import uuid4 as uuid
from time import sleep
import threading

from .common import log
from .mqttsender import Mqtt


class MessageHandler:

    def __init__(self):
        self.resources = {}
        self.loaded = False

    def load_resources(self):
        if not self.loaded:
            log('Loading resources...')
            from main.models import Sensor, Switch

            for model in (Sensor, Switch):
                qs = model.objects.all()
                for obj in qs:
                    log(obj)
                    obj.connect(obj.topic)
                    self.resources.update({obj.uid: obj})
            self.loaded = True

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
