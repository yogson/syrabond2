import json
from datetime import datetime, timedelta

import django.db.models
from django.utils import timezone
from django.db import models
from django.db.models import JSONField
from django.core.validators import validate_comma_separated_integer_list
from typing import List

from main.ops import mqtt_sender, mqtt_listener
from .tasks_interface import Taskable
from main.utils import get_resources, get_classes, instance_klass
from .common import log


DAYS_OF_WEEK = (
    (0, 'Monday'),
    (1, 'Tuesday'),
    (2, 'Wednesday'),
    (3, 'Thursday'),
    (4, 'Friday'),
    (5, 'Saturday'),
    (6, 'Sunday'),
)


class BaseModel(models.Model):

    updated_at = models.DateTimeField(
        verbose_name='Обновлено',
        auto_now=True
    )

    class Meta:
        abstract = True


class TitledModel(models.Model):

    title = models.CharField(
        verbose_name='Имя',
        max_length=100,
        default='Unnamed'
    )

    def __str__(self):
        return self.title

    class Meta:
        abstract = True


class StatedModel(models.Model):

    state = models.JSONField(
        verbose_name='Состояние',
        blank=True,
        null=False,
        default=dict
    )

    @property
    def channels(self):
        return list(self.state.keys())

    def get_state(self, channel=None):
        if self.state is None:
            self.state = {}
            self.save()
            return None
        else:
            if channel:
                return self.state.get(channel)
            else:
                return self.state.get('state') or self.state.get('data')

    get_state.short_description = 'Состояние'

    def update_state(self, state, channel=None):
        if isinstance(state, str) and state.isdigit():
            state = float(state)
        if channel:
            if self.state:
                self.state.update({channel: state})
            else:
                self.state = {channel: state}
        else:
            self.state = {'state': state}

        self.save()

    class Meta:
        abstract = True


class UsingChannelsModel(models.Model):

    channel = models.CharField(
        max_length=50,
        choices=(('state', 'state'), ),
        verbose_name='Канал устройства',
        null=True,
        default='state'
    )

    class Meta:
        abstract = True


class Button(BaseModel, TitledModel, StatedModel):

    latching = models.BooleanField(
        verbose_name='фиксация',
        null=False,
        default=False
    )

    actions = models.ManyToManyField(
        'Action',
        verbose_name='действия',
        related_name="buttons",
        blank=True
    )

    push_out_actions = models.ManyToManyField(
        'Action',
        verbose_name='обратные действия',
        related_name="push_out_buttons",
        blank=True
    )

    def push(self):
        if self.latching and self.get_state() == 'on':
            for action in self.push_out_actions.all():
                action.do()
            self.update_state('off')
            return

        for action in self.actions.all():
            action.do()

        self.update_state('on') if self.latching else None


    class Meta:
        verbose_name = 'Кнопка',
        verbose_name_plural = 'Кнопки'


class Facility(BaseModel, TitledModel):

    key = models.CharField(verbose_name='код', max_length=10)

    def __str__(self):
        return f'{self.title} {self.key}'

    class Meta:
        verbose_name = 'Объект',
        verbose_name_plural = 'Объекты'


class Group(BaseModel, TitledModel):

    key = models.CharField(verbose_name='код', max_length=10)

    @property
    def switches(self):
        return get_resources(self, qs='switch_resources')

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = 'Группа',
        verbose_name_plural = 'Группы'


class Aggregate(BaseModel, TitledModel):

    switches = models.ManyToManyField(
        'Switch',
        verbose_name='Выключатели',
        related_name="aggregates",
        blank=True
    )

    sensors = models.ManyToManyField(
        'Sensor',
        verbose_name='Датчики',
        related_name="aggregates",
        blank=True
    )

    scenarios = models.ManyToManyField(
        'Scenario',
        verbose_name='Сценарии',
        related_name="aggregates",
        blank=True
    )


class Tag(BaseModel, TitledModel):

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = 'Тэг',
        verbose_name_plural = 'Тэги'


class Premise(BaseModel, TitledModel):

    location = models.ForeignKey(
        'self',
        verbose_name='Местонахождение',
        related_name='nested',
        blank=True,
        null=True,
        on_delete=models.CASCADE
    )

    thermostat_follow = models.ForeignKey(
        'self',
        verbose_name='Внешний термостат',
        related_name='followers',
        blank=True,
        null=True,
        on_delete=models.CASCADE
    )

    thermostat = models.FloatField(
        verbose_name='Термостат',
        blank=True,
        null=True,
        default=20
    )

    heating_sensor = models.ForeignKey(
        'Sensor',
        verbose_name='Датчик',
        related_name='prems',
        blank=True,
        null=True,
        on_delete=models.CASCADE
    )

    heating_controller = models.ForeignKey(
        'HeatingController',
        verbose_name='Контроллер отопления',
        related_name='prems',
        blank=True,
        null=True,
        on_delete=models.CASCADE
    )

    def set_thermostat(self, settings):
        try:
            self.thermostat = float(settings)
        except ValueError as e:
            print(e)

    def set_lights(self, settings):
        lights = self.lights
        for light in lights:
            if hasattr(light, settings):
                getattr(light, settings)()

    @property
    def temp(self):
        return self.heating_sensor.state.get(
            'state', self.heating_sensor.state.get('temp')) if self.heating_sensor else '---'

    @property
    def hum(self):
        return self.heating_sensor.state.get(
            'state', self.heating_sensor.state.get('hum', '---')) if self.heating_sensor else '---'

    @property
    def switches(self):
        return get_resources(self, qs='switch_resources')

    @property
    def lights(self):

        def get_nested(location: Premise, acc=[self]):
            if location.nested:
                acc += location.nested.all()
                for loc in location.nested.all():
                    get_nested(loc, acc)
            return acc

        return Switch.objects.filter(location__in=get_nested(self))

    @property
    def lights_str(self):
        return self.switch_resources.all()

    def sensors(self):
        return get_resources(self, qs='sensor_resources')

    def __str__(self):
        return f'{self.title} {self.location if self.location else ""}'

    class Meta:
        verbose_name = 'Местоположение',
        verbose_name_plural = 'Местоположения'


class Resource(BaseModel, TitledModel):

    uid = models.CharField(
        primary_key=True,
        verbose_name='Идентификатор',
        max_length=50,
        blank=False,
        null=False,
        db_index=True
    )

    facility = models.ForeignKey(
        Facility,
        verbose_name='Объект',
        related_name="%(class)s_resources",
        blank=False,
        null=False,
        default=1,
        on_delete=models.CASCADE
    )

    group = models.ForeignKey(
        Group,
        verbose_name='Группа',
        related_name="%(class)s_resources",
        blank=True,
        null=True,
        on_delete=models.CASCADE
    )

    location = models.ForeignKey(
        Premise,
        verbose_name='Расположение',
        related_name="%(class)s_resources",
        blank=True,
        null=True,
        on_delete=models.CASCADE
    )

    tags = models.ManyToManyField(
        Tag,
        verbose_name='Тэги',
        related_name="%(class)s_resources",
        blank=True
    )

    extra = JSONField(
        verbose_name='Прочее',
        blank=True,
        null=False,
        default=dict
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __str__(self):
        return f'{self.title} {self.uid}'

    def __repr__(self):
        return str(self)

    @property
    def topic(self):
        return self.facility.key+'/'+self.type+'/'+self.uid

    @property
    def type(self):
        return self._meta.model_name

    class Meta:
        abstract = True
        verbose_name = 'Устройство',
        verbose_name_plural = 'Устройства'


class VirtualDevice(BaseModel, TitledModel, StatedModel):

    virtual_class = models.CharField(
        verbose_name='Класс плагина',
        max_length=50,
        blank=False,
        null=False,
        choices=get_classes()
    )

    settings = models.JSONField(
        verbose_name='Настройки',
        blank=True,
        null=False,
        default=dict
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.pk:
            self.engage()

    def __str__(self):
        return f'{self.title} {self.virtual_class}'

    def engage(self):
        inst = instance_klass(self.virtual_class, settings=self.settings, state=self.state)
        data = inst()
        if isinstance(data, dict):
            for channel, state in data.items():
                self.update_state(state, channel=channel)
        else:
            self.update_state(data)

    @property
    def state_clear(self):
        return self.state.get('state')

    class Meta:
        verbose_name = 'Виртуальное устройство',
        verbose_name_plural = 'Виртуальные устройства'


class ConnectedResource(Resource):
    sender = mqtt_sender
    listener = mqtt_listener

    @classmethod
    def connect(cls, topic):
        cls.listener.subscribe(topic)

    class Meta:
        abstract = True
        verbose_name = 'Устройство',
        verbose_name_plural = 'Устройства'


class HeatingControllerApp(ConnectedResource):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def turn(self, circuit, position: str):
        try:
            topic = self.topic + '/' + circuit.key
            message = position
            # self.listener.mqttsend(topic, message, retain=True) TODO refactor all the class!
            circuit.state = position
            circuit.save()
            return True
        except Exception as e:
            log(f'Error while turning {self.uid} {position}: {e}')
            return False

    class Meta:
        abstract = True


class SwitchApp(ConnectedResource, StatedModel, Taskable):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def state_(self):
        return self.get_state()

    def switch(self, cmd):
        if hasattr(SwitchApp, cmd):
            getattr(self, cmd)()

    def publish_cmd(self, cmd):
        try:
            self.sender.mqttsend(self.topic, cmd, retain=True)
            # self.update_state(cmd)
            return True
        except Exception as e:
            print(f'Error while publishing {self.uid} {cmd}: {e}')
            return False

    def _turn(self, position, direct=False):
        # Process direct command
        if direct:
            return self.publish_cmd(position)
        # Process indirect command (automation, etc)
        if datetime.fromtimestamp(self.extra.get('freeze_until', 0)) <= datetime.now():
            self.extra.update({'freeze_until': datetime.timestamp(datetime.now() + timedelta(minutes=1))})
            self.save()
            self.publish_cmd(position)

    def schedule_task(self, scheduled: datetime, command: str):
        action, _ = Action.objects.get_or_create(
            switch=self,
            state=command
        )
        return self.create_task(action=action, scheduled=scheduled)

    @property
    def switched_off(self):
        return self.state_ == 'off'

    @property
    def switched_on(self):
        return self.state_ == 'on'

    class Meta:
        abstract = True


class SensorApp(ConnectedResource):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def topic(self):
        return self.facility.key + '/' + self.type + '/' + self.uid + '/#'

    class Meta:
        abstract = True


class Switch(SwitchApp):

    behavior = models.ForeignKey(
        'Behavior',
        verbose_name='Поведение',
        related_name='switches',
        blank=True,
        null=True,
        on_delete=models.CASCADE
    )

    regulator = models.ForeignKey(
        'Regulator',
        verbose_name='Регулятор',
        related_name='switches',
        blank=True,
        null=True,
        on_delete=models.CASCADE
    )

    auto_off_after = models.TimeField(
        verbose_name='Выключить через',
        blank=True,
        null=True
    )

    controlled = models.BooleanField(
        verbose_name='Управляется',
        blank=False,
        default=False
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def update_state(self, state, channel=None):
        super().update_state(state, channel=None)
        self._process_new_state(state)

    def _process_new_state(self, state):
        if state == 'on':
            if self.auto_off_after:
                self._schedule_auto_off()

        # HERE you can put some state processing logics

    def on(self, direct=False):
        self._turn('on', direct)

    def _schedule_auto_off(self):
        scheduled_on = timezone.now() + timedelta(
            hours=self.auto_off_after.hour,
            minutes=self.auto_off_after.minute,
            seconds=self.auto_off_after.second)
        self.schedule_task(scheduled_on, 'off')

    def off(self, direct=False):
        self._turn('off', direct)

    def toggle(self):
        try:
            if self.switched_off:
                self.on(direct=True)
            elif self.switched_on:
                self.off(direct=True)
            return True
        except Exception as e:
            print(f'Error while toggling {self.uid}: {e}')
            return False

    class Meta:
        verbose_name = 'Выключатель',
        verbose_name_plural = 'Выключатели'


class Sensor(SensorApp, StatedModel):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    class Meta:
        verbose_name = 'Датчик',
        verbose_name_plural = 'Датчики'


class HeatingCircuit(BaseModel):

    key = models.CharField(
        verbose_name='Ключ',
        max_length=32,
        null=True,
        blank=True
    )

    premise = models.ForeignKey(
        Premise,
        verbose_name='Помещение',
        related_name="circuits",
        blank=True,
        null=True,
        on_delete=models.CASCADE
    )

    state = models.JSONField(
        verbose_name='Состояние',
        blank=True,
        null=True
    )

    def open(self):
        if not self.state == 'open':
            self.controller.first()._turn(self) if self.controller.first() else None

    def close(self):
        if not self.state == 'close':
            self.controller.first()._turn(self) if self.controller.first() else None


class HeatingController(HeatingControllerApp):

    circuits = models.ManyToManyField(
        HeatingCircuit,
        verbose_name='Контуры',
        related_name="controller",
        blank=True
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    class Meta:
        verbose_name = 'Контроллер отопления',
        verbose_name_plural = 'Контроллеры отопления'


class Regulator(BaseModel, UsingChannelsModel):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._meta.get_field('channel').choices = [(ch, ch) for ch in self.sensor.channels]

    sensor = models.ForeignKey(
        Sensor,
        verbose_name='Датчик',
        related_name='regulators',
        on_delete=models.CASCADE,
        blank=False
    )

    lower_bond = models.FloatField(
        verbose_name='Нижний порог',
        blank=False
    )

    upper_bond = models.FloatField(
        verbose_name='Верхний порог',
        blank=False
    )

    class Directions(models.IntegerChoices):
        direct = True
        reverse = False

    direction = models.BooleanField(
        verbose_name='Действие',
        choices=Directions.choices,
        null=False,
        default=True
    )

    def set_channels(self):
        self.channel

    def signal(self):
        self.sensor.refresh_from_db()
        metric = self.sensor.get_state(self.channel)
        try:
            metric = float(metric)
        except (ValueError, TypeError):
            return
        if metric >= self.upper_bond:
            return not self.direction
        if metric <= self.lower_bond:
            return self.direction

    def engage(self):
        for switch in self.switches.filter(controlled=True):
            if self.signal() is True and switch.switched_off:
                switch.on()
            if self.signal() is False and switch.switched_on:
                switch.off()

    def __str__(self):
        return f"{dict(self.Directions.choices).get(self.direction)} regulator of {self.sensor} ({self.upper_bond}->{self.lower_bond})"

    class Meta:
        verbose_name = 'Регулятор',
        verbose_name_plural = 'Регуляторы'


class Schedule(BaseModel, UsingChannelsModel):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.pk and self.calc_time:
            self._meta.get_field('channel').choices = [(ch, ch) for ch in self.calc_time.channels]

    daily = models.BooleanField(
        verbose_name='Ежедневно',
        null=False,
        blank=False,
        default='True'
    )

    days = models.CharField(
        verbose_name='Дни недели',
        max_length=20,
        validators=(validate_comma_separated_integer_list, ),
        null=True,
        blank=True
    )

    time = models.TimeField(
        verbose_name='Время',
        null=True,
        blank=True
    )

    calc_time = models.ForeignKey(
        'VirtualDevice',
        verbose_name='Виртуальное устройство',
        related_name="schedules",
        blank=True,
        null=True,
        on_delete=models.CASCADE
    )

    scenario = models.ForeignKey(
        'Scenario',
        verbose_name='Сценарий',
        related_name='schedules',
        on_delete=models.CASCADE

    )

    def check_schedule(self):
        now = timezone.now()
        time = self.time or self.parse_time(self.calc_time.get_state(self.channel))

        if self.daily:
            return all((
                time.hour == now.hour,
                time.minute == now.minute
            ))
        else:
            return all((
                str(now.isoweekday()) in self._days_list,
                time.hour == now.hour,
                time.minute == now.minute
            ))

    @staticmethod
    def parse_time(time_string: str) -> datetime:
        if ':' in time_string:
            try:
                return datetime.strptime(time_string, '%H:%M')
            except ValueError:
                pass
            try:
                return datetime.strptime(time_string, '%H:%M:%S')
            except ValueError:
                pass

    @property
    def _days_list(self):
        return [int(item.strip()) for item in self.days.split(',')]

    @property
    def is_today(self):
        if self.daily:
            return True
        if timezone.now().isoweekday() in self._days_list:
            return True
        return False

    @property
    def next_fire(self):
        now = timezone.now()
        time = self.time or self.parse_time(self.calc_time.get_state(self.channel))

        def get_next_day(today: int, days_list: List[int]):
            days_list = sorted(days_list)
            for day in days_list:
                if day >= today:
                    return now.date() + timedelta(days=day - today)

            return now.date() + timedelta(days=7 - today + days_list[0])

        next_fire_day = now.date() if self.is_today else get_next_day(now.isoweekday(), self._days_list)

        if time:
            return datetime(
                    next_fire_day.year, next_fire_day.month, next_fire_day.day) + timedelta(
                hours=time.hour, minutes=time.minute)

    def save(self, *args, **kwargs):
        if self.time:
            self.time = self.time.replace(self.time.hour, self.time.minute, 0, 0)

        if self.daily:
            self.days = None

        super().save(*args, **kwargs)

    def __str__(self):
        return f'Расписание {self.pk}'

    class Meta:
        verbose_name = 'Расписание',
        verbose_name_plural = 'Расписания'


class Condition(BaseModel, UsingChannelsModel):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.pk:
            self._meta.get_field('channel').choices = [(ch, ch) for ch in self.object.channels]

    switch = models.ForeignKey(
        Switch,
        verbose_name='Выключатель',
        related_name="conditions",
        blank=True,
        null=True,
        on_delete=models.CASCADE
    )

    button = models.ForeignKey(
        Button,
        verbose_name='Кнопка',
        related_name="conditions",
        blank=True,
        null=True,
        on_delete=models.CASCADE
    )

    sensor = models.ForeignKey(
        Sensor,
        verbose_name='Датчик',
        related_name="conditions",
        blank=True,
        null=True,
        on_delete=models.CASCADE
    )

    virtual_device = models.ForeignKey(
        'VirtualDevice',
        verbose_name='Виртуальное устройство',
        related_name="conditions",
        blank=True,
        null=True,
        on_delete=models.CASCADE
    )

    comparison = models.CharField(
        verbose_name='Сравнение',
        max_length=2,
        choices=(
            ('>', '>'),
            ('<', '<'),
            ('==', '='),
            ('!=', '<>')
        ),
        null=False,
        blank=False,
        default='=='
    )

    state = models.CharField(
        verbose_name='Состояние',
        max_length=32,
        null=True,
        blank=True
    )

    @property
    def object(self):
        return self.sensor if self.sensor else self.button if self.button\
            else self.switch if self.switch else self.virtual_device

    def check_condition(self):
        state = self.object.state.get(self.channel if self.channel else 'state')
        state = str(state).lower()
        return eval(f'"{state}" {self.comparison} "{self.state.lower()}"')

    def __str__(self):
        return f'{self.object} {(str(self.channel) + " ") if self.channel else ""}{self.comparison} {self.state}'

    class Meta:
        verbose_name = 'Условие',
        verbose_name_plural = 'Условия'


class Action(BaseModel, Taskable):

    switch = models.ForeignKey(
        Switch,
        verbose_name='Выключатель',
        related_name="actions",
        blank=True,
        null=True,
        on_delete=models.CASCADE
    )

    state = models.CharField(
        verbose_name='Состояние',
        max_length=12,
        choices=(
            ('on', 'on'),
            ('off', 'off'),
            ('toggle', 'toggle'),
            ('push', 'push')
        ),
        null=True,
        blank=False,
        default='on'
    )

    def __str__(self):
        return f'{self.switch if self.switch else None} = {self.state}'

    def schedule_task(self, scheduled: datetime):
        return self.create_task(action=self, scheduled=scheduled)

    def do(self):
        log('Performing the action ' + str(self))
        try:
            self.switch.__getattribute__(self.state)()
        except Exception as e:
            log(f'Failed to perform {self}: {e}')

    class Meta:
        verbose_name = 'Действие',
        verbose_name_plural = 'Действия'


class ConditionTypedModel(models.Model):

    conditions_type = models.CharField(
        verbose_name='Сочетание условий',
        max_length=1,
        choices=(
            ('&', 'A & B'),
            ('|', 'A | B')
        ),
        null=False,
        blank=False,
        default='&'
    )

    def target_conditions(self, conditions: django.db.models.QuerySet):
        if conditions.none():
            return False
        all_conditions = (condition.check_condition() for condition in conditions.all())
        if self.conditions_type == '|':
            return any(all_conditions)
        else:
            return all(all_conditions)

    class Meta:
        abstract = True


class Behavior(BaseModel, TitledModel, ConditionTypedModel):

    conditions_on = models.ManyToManyField(
        Condition,
        verbose_name='Условия включения',
        related_name="behaviors_on",
        blank=True
    )

    conditions_off = models.ManyToManyField(
        Condition,
        verbose_name='Условия выключения',
        related_name="behaviors_off",
        blank=True
    )

    @property
    def on(self):
        return self.target_conditions(self.conditions_on)

    @property
    def off(self):
        if self.conditions_off.exists():
            return self.target_conditions(self.conditions_off)
        return not self.on

    def engage(self):

        if self.off:
            for switch in self.switches.filter(controlled=True):
                if switch.state_ == 'on':
                    switch.off()
                    return
        if self.on:
            for switch in self.switches.filter(controlled=True):
                if switch.state_ == 'off':
                    switch.on()

    class Meta:
        verbose_name = 'Поведение',
        verbose_name_plural = 'Шаблоны поведения'


class Scenario(BaseModel, TitledModel, ConditionTypedModel, Taskable):

    conditions = models.ManyToManyField(
        Condition,
        verbose_name='Условия',
        related_name="scenarios",
        blank=True
    )

    actions = models.ManyToManyField(
        Action,
        verbose_name='Действия',
        related_name="scenarios",
        blank=True
    )

    buttons = models.ManyToManyField(
        Button,
        verbose_name='Нажимаемые кнопки',
        related_name="scenarios",
        blank=True
    )

    active = models.BooleanField(
        verbose_name='Активен',
        null=False,
        blank=False,
        default=False
    )

    def work_out(self):
        log('Running the scenario ' + str(self))
        for action in self.actions.all():
            action.do()
        for button in self.buttons.all():
            button.push()

    @property
    def its_time(self):
        return any((
            schedule.check_schedule() for schedule in self.schedules.all()
        ))

    def schedule_task(self, scheduled: datetime):
        return self.create_task(scenario=self, scheduled=scheduled)

    def engage(self):
        if self.active and self.its_time and self.target_conditions(conditions=self.conditions):
            self.work_out()

    def save(self, *args, **kwargs):
        if self.id and not self.conditions.exists():
            self.conditions_type = '&'

        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = 'Сценарий',
        verbose_name_plural = 'Сценарии'
