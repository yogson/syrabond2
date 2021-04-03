from rest_framework import viewsets, serializers
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from .models import Switch, Sensor, Premise, Facility, Group, HeatingController
from .serializers import SwitchSerializer, SensorSerializer, PremiseSerializer, GroupSerializer, \
    HeatingControllerSerializer


class SwitchViewSet(viewsets.ViewSet):

    def list(self, request):
        queryset = Switch.objects.all()
        serializer = SwitchSerializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        queryset = Switch.objects.all()
        switch = get_object_or_404(queryset, pk=pk)
        serializer = SwitchSerializer(switch)
        return Response(serializer.data)

    def act(self, request, pk=None, cmd=None):
        queryset = Switch.objects.all()
        switch = get_object_or_404(queryset, pk=pk)
        switch.switch(cmd)
        serializer = SwitchSerializer(switch)
        return Response(serializer.data)


class SensorViewSet(viewsets.ViewSet):

    def list(self, request):
        queryset = Sensor.objects.all()
        serializer = SensorSerializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        queryset = Sensor.objects.all()
        sensor = get_object_or_404(queryset, pk=pk)
        serializer = SensorSerializer(sensor)
        return Response(serializer.data)


class FacilityViewSet(viewsets.ViewSet):

    def list(self, request):
        queryset = Facility.objects.all()
        serializer = serializers.ModelSerializer(queryset)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        queryset = Facility.objects.all()
        facility = get_object_or_404(queryset, pk=pk)
        serializer = serializers.ModelSerializer(facility)
        return Response(serializer.data)


class PremiseViewSet(viewsets.ViewSet):

    def list(self, request):
        queryset = Premise.objects.all()
        serializer = PremiseSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)

    def top(self, request):
        queryset = Premise.objects.filter(location__isnull=True).filter(nested__isnull=False).distinct()
        serializer = PremiseSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        queryset = Premise.objects.all()
        prem = get_object_or_404(queryset, pk=pk)
        serializer = PremiseSerializer(prem, context={'request': request})
        return Response(serializer.data)

    def set_thermo(self, request, pk=None, setting=None):
        queryset = Premise.objects.all()
        prem = get_object_or_404(queryset, pk=pk)
        prem.set_thermostat(request.data.get("value"))
        prem.save()
        serializer = PremiseSerializer(prem, context={'request': request})
        return Response(serializer.data)

    def set_lights(self, request, pk=None):
        queryset = Premise.objects.all()
        prem = get_object_or_404(queryset, pk=pk)
        prem.set_lights(request.data.get('cmd'))
        serializer = PremiseSerializer(prem, context={'request': request})
        return Response(serializer.data)


class GroupViewSet(viewsets.ViewSet):

    def list(self, request):
        queryset = Group.objects.all()
        serializer = GroupSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        queryset = Group.objects.all()
        obj = get_object_or_404(queryset, pk=pk)
        serializer = GroupSerializer(obj, context={'request': request})
        return Response(serializer.data)


class HeatingControllerViewSet(viewsets.ViewSet):

    def list(self, request):
        queryset = HeatingController.objects.all()
        serializer = HeatingControllerSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        queryset = HeatingController.objects.all()
        obj = get_object_or_404(queryset, pk=pk)
        serializer = HeatingControllerSerializer(obj, context={'request': request})
        return Response(serializer.data)