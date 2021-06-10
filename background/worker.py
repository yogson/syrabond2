from threading import Thread
from time import sleep
from random import randrange

from main.models import Scenario, Behavior, Regulator, StatedVirtualDevice


class RegularHandler:

    def __init__(self, klass):
        self.klass = klass
        self.instances = []

    def refresh(self):
        self.instances = list(self.klass.objects.all())

    def check(self):
        for item in self.instances:
            item.engage()


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


handler_classes = (Scenario, Behavior, Regulator, StatedVirtualDevice)
handlers = [RegularHandler(klass) for klass in handler_classes]


def loop():
    # Init handlers
    for handler in handlers:
        handler.refresh()

    while 1:
        for handler in handlers:
            if randrange(0, 5) == 4:
                handler.refresh()
            handler.check()
        sleep(5)


while 1:
    t = Thread(target=loop, daemon=True)
    print('Running background automation daemon...')
    t.start()
    t.join()

