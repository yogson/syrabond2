from rest_framework import serializers
from rest_framework.reverse import reverse

from .models import Switch, Sensor, Premise, Group, HeatingController


class SwitchSerializer(serializers.ModelSerializer):

    state = serializers.CharField(source='get_state', read_only=True)

    class Meta:
        fields = ('title', 'uid', 'state')

        model = Switch


class SensorSerializer(serializers.ModelSerializer):

    class Meta:
        fields = ('title', 'uid', 'state')

        model = Sensor


class GroupSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        fields = ('key', 'switch_resources', 'sensor_resources')

        model = Group


class HeatingControllerSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        fields = ('pk', 'circuits')

        model = HeatingController

class PremiseSerializer(serializers.HyperlinkedModelSerializer):

    lights = serializers.HyperlinkedRelatedField(
        many=True,
        view_name='switch-detail',
        queryset=Premise.lights,

    )

    class Meta:
        depth = 1
        fields = (
            'pk', 'title', 'nested', 'location', 'thermostat',
            'temp', 'hum', 'switch_resources', 'sensor_resources', 'lights')
        model = Premise


