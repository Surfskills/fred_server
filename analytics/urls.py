from django.urls import path
from .views import OrderAnalyticsView, GeneralAnalyticsView

urlpatterns = [
    path('order-analytics/<str:service_id>/', OrderAnalyticsView.as_view(), name='order_analytics'),
    path('order-analytics/<str:service_id>/<str:type>/pdf/', OrderAnalyticsView.as_view(), name='order_pdf'),
    path('general-analytics/', GeneralAnalyticsView.as_view(), name='general_analytics'),
]
