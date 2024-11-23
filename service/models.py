from django.db import models
from authentication.models import User
from fred import settings

class Service(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='authentication_services'
    )
    title = models.CharField(max_length=255)
    description = models.TextField()
    cost = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_time = models.CharField(max_length=100)  # e.g., "2-3 weeks"
    support_duration = models.CharField(max_length=100)  # e.g., "1 month"
    features = models.JSONField()  # Stores an array of features
    process_link = models.URLField()
    service_id = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.title


