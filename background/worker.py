from threading import Thread
from time import sleep
from random import randrange

import uwsgidecorators

from main.common import log
from main.models import Scenario, Behavior, Regulator, StatedVirtualDevice
from main.ops import mqtt
from syrabond2 import settings


class RegularHandler:

    def __init__(self, klass):
        self.klass = klass
        self.instances = []

    def refresh(self):
        self.instances = list(self.klass.objects.all())

    def check(self):
        for item in self.instances:
            item.engage()


handler_classes = (Scenario, Behavior, Regulator, StatedVirtualDevice)
handlers = [RegularHandler(klass) for klass in handler_classes]


@uwsgidecorators.thread
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


t = Thread(target=loop, daemon=True)
log('Running background daemon...')
t.start()
