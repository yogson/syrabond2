from time import sleep
import abc

from main.common import log
from main.models import Scenario, Behavior, Regulator, VirtualDevice
from tasks.models import Task
from main.ops import mqtt


class Handler:

    @abc.abstractmethod
    def refresh(self):
        pass

    @abc.abstractmethod
    def check(self):
        pass


class RegularHandler(Handler):

    def __init__(self, klass):
        self.klass = klass
        self.instances = []

    def refresh(self):
        self.instances = list(self.klass.objects.all())

    def check(self):
        for item in self.instances:
            item.engage()


class TaskHandler(Handler):

    def __init__(self):
        self.instances = []

    def refresh(self):
        self.instances = list(Task.objects.filter(done=False))
        Task.objects.filter(done=True).delete()

    def check(self):
        for item in self.instances:
            item.do()


handler_classes = (Scenario, Behavior, Regulator, VirtualDevice)
handlers = [RegularHandler(klass) for klass in handler_classes] + [TaskHandler()]


def loop():
    # Init handlers
    mqtt.external_handler.load_resources()

    for handler in handlers:
        handler.refresh()

    c = 0

    while 1:
        # Check for new messages
        mqtt.check_for_messages()

        for handler in handlers:
            handler.refresh()
            handler.check()

        sleep(1)


log('Running background daemon...')
loop()
