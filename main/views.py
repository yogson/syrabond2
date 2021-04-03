from rest_framework import generics

from .models import Switch
from .serializers import SwitchSerializer


class SwitchView(generics.ListAPIView):
    queryset = Switch.objects.all()
    serializer_class = SwitchSerializer


class SwitchActionView(generics.UpdateAPIView):
    queryset = Switch.objects.all()
    serializer_class = SwitchSerializer
