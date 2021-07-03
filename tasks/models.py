from datetime import datetime

from django.db import models
from django.db import transaction

import main.models


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

    action = models.ForeignKey(
        'main.Action',
        null=True,
        blank=True,
        related_name='tasks',
        on_delete=models.CASCADE
    )

    def time_for(self):
        now = datetime.now()
        return all((
            now.date() >= self.scheduled_on.date(),
            now.hour >= self.scheduled_on.hour,
            now.minute >= self.scheduled_on.minute
        ))

    def do_action(self):
        if self.action:
            with transaction.atomic():
                try:
                    self.action.do()
                except:
                    return
                self.done = True
                self.save()

    def run_scenario(self):
        if self.scenario:
            with transaction.atomic():
                try:
                    self.scenario.engage()
                except:
                    return
                self.done = True
                self.save()
