from datetime import timedelta, datetime
from time import sleep
from threading import Thread
import abc

from django.utils import timezone

from main.common import log
from main.models import Scenario, Behavior, Regulator, VirtualDevice, Switch, Sensor, Button
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

    def __str__(self):
        return f'handler of {self.klass.__name__}'


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


handler_classes = (Behavior, Regulator, VirtualDevice)  # Behavior
handlers = [RegularHandler(klass) for klass in handler_classes]


def handlers_loop():
    # Init handlers
    for handler in handlers:
        log(f'Initialize {handler}...')
        handler.refresh()
        if handler.instances:
            log(f'Handle instances: {", ".join([str(i) for i in handler.instances])}')

    while 1:
        # Process automation handlers
        for handler in handlers:
            handler.check()

        sleep(1)


def task_add_queue_loop():
    while 1:
        now = timezone.now()
        for scenario in Scenario.objects.filter(active=True):
            for schedule in scenario.schedules.all():
                next_fire = schedule.next_fire
                if next_fire and (now + timedelta(hours=6) >= next_fire > now):
                    task = schedule.scenario.schedule_task(next_fire)  # Do we need the task object?!

        sleep(60)


def process_tasks_queue_loop():
    while 1:

        # Check for new resources in DB
        # TODO remove somewhere from here
        mqtt.external_handler.update_resources()
        # Check for new automation instances in DB
        # TODO remove somewhere from here
        for handler in handlers:
            handler.refresh()

        for task in Task.objects.filter(done=False):
            if task.time_for():
                task.do()
        sleep(15)


def process_messages_loop():
    mqtt.external_handler.load_resources(
        [Switch, Sensor, Button]
    )
    while 1:
        mqtt.wait_for_messages()
        # Wait before reconnect
        sleep(60)


def maintenance_the_system():
    """Perform on-start system maintenance and cleaning"""
    log('Performing system cleanup...')
    # delete old executed tasks
    Task.objects.filter(done=True).filter(
        updated_at__lt=datetime.now() - timedelta(days=30)).delete()


log('Running background daemon...')
maintenance_the_system()

for loop in [process_messages_loop, handlers_loop, process_tasks_queue_loop, task_add_queue_loop]:
    log(f'Starting thread with {loop} loop...')
    Thread(target=loop).start()
    # Let's init slowly
    sleep(1)
