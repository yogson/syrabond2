from django import forms
from django.contrib import admin
from django.db.models import Q


from .models import *


def make_on(modeladmin, request, queryset):
    [n.on(direct=True) for n in queryset]


def make_off(modeladmin, request, queryset):
    [n.off(direct=True) for n in queryset]


def make_connect(modeladmin, request, queryset):
    [n.connect() for n in queryset]


def workout(modeladmin, request, queryset):
    [n.work_out() for n in queryset]


def switches_off(modeladmin, request, queryset):
    resources = []
    for item in queryset:
        resources += item.switches
    [n.off() for n in resources]


def switches_on(modeladmin, request, queryset):
    resources = []
    for item in queryset:
        resources += item.switches
    [n.on() for n in resources]


def check_switches(modeladmin, request, queryset):
    for item in queryset:
        item.engage()

class ScheduleInline(admin.TabularInline):
    model = Schedule
    fk_name = 'scenario'
    extra = 0


class GroupForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['heating_sensor'].queryset = Sensor.objects.filter(
                                                location__id=self.instance.id)


class ControllerForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['circuits'].queryset = HeatingCircuit.objects.filter(
            Q(controller__isnull=True) | Q(controller__uid=self.instance.uid))


class AggForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)
        for field in ('switches', 'sensors', 'scenarios'):
            self.fields[field].widget.can_delete_related = True
            self.fields[field].widget.can_view_related = True
            self.fields[field].widget.can_change_related = True

class AggAdmin(admin.ModelAdmin):
    form = AggForm


class ControllerAdmin(admin.ModelAdmin):
    form = ControllerForm


class PremAdmin(admin.ModelAdmin):
    form = GroupForm
    list_display = ('title', 'thermostat', 'temp', 'hum')


class ResAdmin(admin.ModelAdmin):
    actions = [make_on, make_off]
    list_display = ('title', 'topic', 'state', 'updated_at', 'aggregates')


class GroupAdmin(admin.ModelAdmin):
    actions = [switches_off, switches_on]
    # list_display = ('title', 'uid', 'get_state')


class ConAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'check_condition', )


class BehAdmin(admin.ModelAdmin):
    actions = [check_switches]
    list_display = ('__str__', 'on', 'off')


class RegAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'signal')


class ScenForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.id and self.instance.aggregates.exists():
            self.fields['conditions'].queryset = Condition.objects.filter(scenarios__in=[self.instance])
            self.fields['actions'].queryset = Action.objects.filter(scenarios__in=[self.instance])

        if not self.instance.id:
            self.fields['conditions'].disabled = True
            self.fields['actions'].disabled = True
            self.fields['conditions_type'].disabled = True


class ScenAdmin(admin.ModelAdmin):
    form = ScenForm
    inlines = [
        ScheduleInline,
    ]
    actions = (workout, )
    list_display = ('__str__',)


class StatedVirtualDeviceAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'state_clear', )


admin.site.register(Switch, ResAdmin)
admin.site.register(Sensor, ResAdmin)
admin.site.register(Tag)
admin.site.register(Group, GroupAdmin)
admin.site.register(Channel)
admin.site.register(HeatingController, ControllerAdmin)
admin.site.register(HeatingCircuit)
admin.site.register(Premise, PremAdmin)
admin.site.register(Scenario, ScenAdmin)
admin.site.register(Condition, ConAdmin)
admin.site.register(Action)
admin.site.register(Facility)
admin.site.register(StatedVirtualDevice, StatedVirtualDeviceAdmin)
admin.site.register(Schedule)
admin.site.register(Aggregate, AggAdmin)
admin.site.register(Behavior, BehAdmin)
admin.site.register(Regulator, RegAdmin)
