import abc
from datetime import datetime

import main.models
from main.common import log
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

            task, is_created = cls.TASK.objects.get_or_create(
                    scheduled_on=scheduled,
                    scenario=scenario
                )
            if is_created:
                task.actions.add(*(a.pk for a in scenario.actions.all()))
                log(f'Task was created: {task}')

            return task

        if action:
            task = cls.TASK.objects.create(scheduled_on=scheduled)
            task.actions.add(action)
            task.save()
            return task


Taskable = DBTask
