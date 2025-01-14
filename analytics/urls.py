from django.urls import path
from .views import OrderAnalyticsView, GeneralAnalyticsView

urlpatterns = [
    path('order-analytics/<str:id>/', OrderAnalyticsView.as_view(), name='order_analytics'),
    path('order-analytics/<str:id>/<str:type>/pdf/', OrderAnalyticsView.as_view(), name='order-analytics-pdf'),
    path('general-analytics/', GeneralAnalyticsView.as_view(), name='general_analytics'),
]
