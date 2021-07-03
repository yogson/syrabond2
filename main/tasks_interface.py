import abc
from datetime import datetime

from tasks.models import Task


class AbstractTask:

    @classmethod
    @abc.abstractmethod
    def create_task(cls, scheduled: datetime, scenario=None, action=None):
        pass


class DBTask(AbstractTask):

    TASK = Task

    @classmethod
    def create_task(cls, scheduled: datetime, scenario=None, action=None):

        if scenario:
            return cls.TASK.objects.get_or_create(
                scheduled_on=scheduled,
                scenario=scenario
            )[0]

        if action:
            return cls.TASK.objects.get_or_create(
                scheduled_on=scheduled,
                action=action
            )[0]


Taskable = DBTask
