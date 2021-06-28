from time import sleep
from random import randrange
from uuid import uuid4

from main.common import log, MessageHandler
from main.models import Scenario, Behavior, Regulator, VirtualDevice
from main.mqttsender import Mqtt


class RegularHandler:

    def __init__(self, klass):
        self.klass = klass
        self.instances = []

    def refresh(self):
        self.instances = list(self.klass.objects.all())

    def check(self):
        for item in self.instances:
            item.engage()


handler_classes = (Scenario, Behavior, Regulator, VirtualDevice)
handlers = [RegularHandler(klass) for klass in handler_classes]


def loop():
    # Init handlers
    mqtt.external_handler.load_resources()

    for handler in handlers:
        handler.refresh()

    c = 0

    while 1:
        # Check for new messages
        mqtt.check_for_messages()

        if c > 3:
            for handler in handlers:
                if randrange(0, 5) == 4:
                    handler.refresh()
                handler.check()
            c = 0

        c += 1
        sleep(1)


mqtt = Mqtt('syrabond_automation_' + str(uuid4()), clean_session=False, handler=MessageHandler())
log('Running background daemon...')
#loop()
