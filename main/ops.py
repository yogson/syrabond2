from uuid import uuid4 as uuid
from time import sleep
import threading

from .mqttsender import Mqtt
from .heating_control import HeatingController


class MessageHandler:

    def __init__(self):
        self.resources = {}
        self.loaded = False

    def load_resources(self):
        if not self.loaded:
            print('loading...')
            from main.models import Sensor, Switch

            for model in (Sensor, Switch):
                qs = model.objects.all()
                for obj in qs:
                    print(obj)
                    obj.connect(obj.listener, obj.topic)
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


mqtt = Mqtt('syrabond_server_' + str(uuid()), clean_session=False, handler=MessageHandler())


def process_messages():
    sleep(5)
    mqtt.external_handler.load_resources()
    while True:
        sleep(1)
        mqtt.check_for_messages()


t = threading.Thread(target=process_messages, daemon=True)
t.start()
