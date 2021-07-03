from datetime import datetime, timedelta
from time import sleep
from threading import Thread
import abc

from django.utils import timezone

from main.common import log
from main.models import Scenario, Behavior, Regulator, VirtualDevice
from tasks.models import Task
from main.ops import mqtt_listener as mqtt


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

    # Maybe next time... For now we will use process_tasks_queue_loop

    def __init__(self):
        self.instances = []

    def refresh(self):
        self.instances = list(Task.objects.filter(done=False))
        Task.objects.filter(done=True).delete()

    def check(self):
        for item in self.instances:
            item.do()


handler_classes = (Scenario, Behavior, Regulator, VirtualDevice)
handlers = [RegularHandler(klass) for klass in handler_classes]


def handlers_loop():
    # Init handlers
    mqtt.external_handler.load_resources()

    for handler in handlers:
        handler.refresh()

    while 1:
        # Check for new messages
        mqtt.check_for_messages()

        for handler in handlers:
            handler.refresh()
            handler.check()

        sleep(1)


def task_add_queue_loop():
    while 1:
        now = timezone.now()
        #actual_tasks = Task.objects.filter(created_at__gt=datetime.now() - timedelta(hours=6))
        for scenario in Scenario.objects.filter(active=True):
            for schedule in scenario.schedules.all():
                if now + timedelta(hours=6) >= schedule.next_fire > now:
                    schedule.scenario.schedule_task(schedule.next_fire)
        sleep(60)


def process_tasks_queue_loop():
    while 1:
        for task in Task.objects.filter(done=False):
            if task.time_for():
                task.run_scenario()
                task.do_action()
        sleep(15)


log('Running background daemon...')

for loop in [handlers_loop, process_tasks_queue_loop, task_add_queue_loop]:
    Thread(target=loop).start()
