from django.urls import path

from . import viewsets

urlpatterns = [
    path('facility/<str:pk>/', viewsets.FacilityViewSet.as_view({'get': 'retrieve'}), name='facility-detail'),
    path('group/', viewsets.GroupViewSet.as_view({'get': 'list'}), name='group-list'),
    path('group/<str:pk>/', viewsets.GroupViewSet.as_view({'get': 'retrieve'}), name='group-detail'),
    path('hcontroller/', viewsets.HeatingControllerViewSet.as_view({'get': 'list'}), name='heatingcontroller-list'),
    path('hcontroller/<str:pk>/', viewsets.HeatingControllerViewSet.as_view({'get': 'retrieve'}), name='heatingcontroller-detail'),
    path('switch/', viewsets.SwitchViewSet.as_view({'get': 'list'})),
    path('switch/<str:pk>/', viewsets.SwitchViewSet.as_view({'get': 'retrieve'}), name='switch-detail'),
    path('switch/<str:pk>/<str:cmd>/', viewsets.SwitchViewSet.as_view({'get': 'act'})),
    path('sensor/', viewsets.SensorViewSet.as_view({'get': 'list'})),
    path('sensor/<str:pk>/', viewsets.SensorViewSet.as_view({'get': 'retrieve'}), name='sensor-detail'),
    path('premises/', viewsets.PremiseViewSet.as_view({'get': 'list'})),
    path('premise/', viewsets.PremiseViewSet.as_view({'get': 'top'})),
    path('premise/<str:pk>/', viewsets.PremiseViewSet.as_view({'get': 'retrieve'}), name='premise-detail'),
    path('premise/<str:pk>/thermo/', viewsets.PremiseViewSet.as_view({'post': 'set_thermo'})),
    path('premise/<str:pk>/lights/', viewsets.PremiseViewSet.as_view({'post': 'set_lights'})),
]