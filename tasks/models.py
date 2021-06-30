from django.db import models
from django.db import transaction

import main.models


class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Task(BaseModel):

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

    def do(self):
        with transaction.atomic():
            try:
                self.action.do()
            except:
                return
            self.done = True
            self.save()
