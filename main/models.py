from django.db import models
from django.db.models import JSONField
from django.core.validators import validate_comma_separated_integer_list

from main.ops import mqtt
from main.utils import get_resources, get_classes, instance_klass


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

    class Meta:
        abstract = True


class TitledModel(models.Model):

    title = models.CharField(
        verbose_name='Имя',
        max_length=100
    )

    def __str__(self):
        return self.title

    class Meta:
        abstract = True


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


class Channel(BaseModel):

    key = models.CharField(verbose_name='Канал', max_length=10)

    def __str__(self):
        return self.key

    class Meta:
        verbose_name = 'Канал',
        verbose_name_plural = 'Каналы'


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
        null=True,
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

    state = models.JSONField(
        verbose_name='Состояние',
        blank=True,
        null=True
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

    def get_state(self):
        if self.state is None:
            return None
        else:
            return self.state.get('state') if self.state.get('state') else self.state.get('data')
    get_state.short_description = 'Состояние'

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


class StatedVirtualDevice(BaseModel):

    virtual_class = models.CharField(
        verbose_name='Класс плагина',
        max_length=50,
        blank=False,
        null=False,
        choices=get_classes()
    )

    state = models.JSONField(
        verbose_name='Состояние',
        blank=True,
        null=True
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.pk:
            self.update_state()


    def __str__(self):
        return self.virtual_class

    def update_state(self):
        inst = instance_klass(self.virtual_class)
        self.state = {
            'state': inst()
        }

    @property
    def state_clear(self):
        return self.state.get('state')

    class Meta:
        verbose_name = 'Виртуальное устройство',
        verbose_name_plural = 'Виртуальные устройства'

class ConnectedStatedResource(Resource):
    listener = mqtt

    @staticmethod
    def connect(listener, topic):
        listener.subscribe(topic)

    def update_state(self, state, channel=None):
        if state.isdigit():
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
        verbose_name = 'Устройство',
        verbose_name_plural = 'Устройства'


class HeatingControllerApp(ConnectedStatedResource):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def turn(self, circuit, position: str):
        try:
            topic = self.topic + '/' + circuit.key
            message = position
            self.listener.mqttsend(topic, message, retain=True)
            circuit.state = position
            circuit.save()
            return True
        except Exception as e:
            print(f'Error while turning {self.uid} {position}: {e}')
            return False

    class Meta:
        abstract = True


class SwitchApp(ConnectedStatedResource):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def __state(self):
        return self.state.get('state')

    def switch(self, cmd):
        if hasattr(SwitchApp, cmd):
            getattr(self, cmd)()

    def _turn(self, position):
        try:
            self.listener.mqttsend(self.topic, position, retain=True)
            self.update_state(position)
            return True
        except Exception as e:
            print(f'Error while turning {self.uid} {position}: {e}')
            return False

    def on(self):
        self._turn('on')

    def off(self):
        self._turn('off')

    def toggle(self):
        try:
            if self.state.get('state') == 'off':
                self._turn('on')
            elif self.state.get('state') == 'on':
                self._turn('off')
            return True
        except Exception as e:
            print(f'Error while toggling {self.uid}: {e}')
            return False

    class Meta:
        abstract = True


class SensorApp(ConnectedStatedResource):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def topic(self):
        return self.facility.key + '/' + self.type + '/' + self.uid + '/#'

    class Meta:
        abstract = True


class Switch(SwitchApp):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    class Meta:
        verbose_name = 'Выключатель',
        verbose_name_plural = 'Выключатели'


class Sensor(SensorApp):

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


class Schedule(BaseModel):

    daily = models.BooleanField(
        verbose_name='Ежедневно',
        null=False,
        blank=False,
        default='False'
    )

    days = models.CharField(
        verbose_name='Дни недели',
        max_length=20,
        validators=(validate_comma_separated_integer_list, )
    )

    time = models.TimeField(
        verbose_name='Время'
    )

    scenario = models.ForeignKey(
        'Scenario',
        verbose_name='Сценарий',
        related_name='schedules',
        on_delete=models.CASCADE
    )

    class Meta:
        verbose_name = 'Расписание',
        verbose_name_plural = 'Расписания'


class Condition(BaseModel):

    switch = models.ForeignKey(
        Switch,
        verbose_name='Выключатель',
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

    channel = models.ForeignKey(
        Channel,
        verbose_name='Канал',
        related_name="conditions",
        blank=True,
        null=True,
        on_delete=models.CASCADE
    )

    virtual_device = models.ForeignKey(
        StatedVirtualDevice,
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
        return self.sensor if self.sensor else self.switch if self.switch else self.virtual_device

    def check_condition(self):
        state = self.object.state.get(self.channel.key if self.channel else 'state')
        return eval(f'"{state}" {self.comparison} "{self.state}"')

    def __str__(self):
        return f'{self.object} {self.comparison} {self.state}'

    class Meta:
        verbose_name = 'Условие',
        verbose_name_plural = 'Условия'


class Action(BaseModel):

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
            ('toggle', 'toggle')
        ),
        null=True,
        blank=False,
        default='on'
    )

    def __str__(self):
        return f'{self.switch if self.switch else None} = {self.state}'

    def do(self):
        self.switch.__getattribute__(self.state)()


    class Meta:
        verbose_name = 'Действие',
        verbose_name_plural = 'Действия'


class Scenario(BaseModel, TitledModel):

    conditions = models.ManyToManyField(
        Condition,
        verbose_name='Условия',
        related_name="scenarios",
        blank=True
    )

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

    actions = models.ManyToManyField(
        Action,
        verbose_name='Действия',
        related_name="scenarios",
        blank=True
    )

    def check_conditions(self):
        conditions = set()
        for cond in self.conditions.all():
            conditions.update({cond.check_condition()})
        if self.conditions_type == '|':
            return True if True in conditions else False
        else:
            return True if conditions == {True} else False

    def work_out(self):
        if self.check_conditions():
            for action in self.actions.all():
                action.do()

    def sched(self):
        return self.schedules.all()


    class Meta:
        verbose_name = 'Сценарий',
        verbose_name_plural = 'Сценарии'