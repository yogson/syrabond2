from datetime import datetime

from django.db import models
from django.db import transaction

from main.common import log


class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Task(BaseModel):

    scenario = models.ForeignKey(
        'main.Scenario',
        null=True,
        blank=True,
        related_name='tasks',
        on_delete=models.CASCADE
    )

    scheduled_on = models.DateTimeField(
        null=True,
        blank=True
    )

    done = models.BooleanField(default=False)

    actions = models.ManyToManyField(
        'main.Action',
        verbose_name='Действия',
        blank=True,
        related_name='tasks'
    )

    def __str__(self):
        return f'Task scheduled on {self.scheduled_on} for {self.scenario}'

    def time_for(self):
        now = datetime.now()
        return all((
            now.date() >= self.scheduled_on.date(),
            now.hour >= self.scheduled_on.hour,
            now.minute >= self.scheduled_on.minute
        ))

    def cancel(self):
        log(f"{self} has been canceled")
        self.delete()

    def do(self):
        log(f'Running the {self}')
        for action in self.actions.all():
            action.do()
        self.done = True
        self.save()
