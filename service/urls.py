from django.urls import path

from service.views import ServiceCreateView


urlpatterns = [
path('create/', ServiceCreateView.as_view(), name='service-create'),
path('', ServiceCreateView.as_view(), name='service-list'),
]
