# from django.db import models
# from django.conf import settings


# class Service(models.Model):
#     # User associated with the service
#     user = models.ForeignKey(
#         settings.AUTH_USER_MODEL, 
#         on_delete=models.CASCADE, 
#         related_name='user_services'
#     )
    
#     # Other fields for service details
#     title = models.CharField(max_length=255)
#     description = models.TextField()
#     cost = models.DecimalField(max_digits=10, decimal_places=2)
    
#     # New fields for sizes and phone number
#     sizes = models.JSONField(default=dict)  
#     phone_number = models.CharField(max_length=20, blank=True, null=True) 

    
#     delivery_time = models.CharField(max_length=100)  # e.g., "2-3 weeks"
#     support_duration = models.CharField(max_length=100)  # e.g., "1 month"
#     features = models.JSONField()  # Stores an array of features
#     process_link = models.URLField()
#     service_id = models.CharField(max_length=100, unique=True)
    
#     # Payment status choices
#     PENDING = 'pending'
#     PAID = 'paid'
#     FAILED = 'failed'
    
#     PAYMENT_STATUS_CHOICES = [
#         (PENDING, 'Pending'),
#         (PAID, 'Paid'),
#         (FAILED, 'Failed'),
#     ]
    
#     # Order status choices
#     ORDER_STATUS_CHOICES = [
#         ('processing', 'Processing'),
#         ('completed', 'Completed'),
#         ('canceled', 'Canceled'),
#         ('shipped', 'Shipped'),
#         ('delivered', 'Delivered'),
#         ('proceed_to_pay', 'Proceed to pay'),
#         ('accepted', 'Accepted'),
#         ('returned', 'Returned'),
#     ]
#         # Add new acceptance status choices
#     ACCEPTANCE_STATUS_CHOICES = [
#         ('pending', 'Pending'),
#         ('accepted', 'Accepted'),
#         ('returned', 'Returned'),
#         ('completed', 'Completed'),
#     ]
#     acceptance_status = models.CharField(
#         max_length=15,
#         choices=ACCEPTANCE_STATUS_CHOICES,
#         default='pending',
#         blank=True,
#         null=True
#     )
#     payment_status = models.CharField(
#         max_length=10,
#         choices=PAYMENT_STATUS_CHOICES,
#         default=PENDING,
#     )
    
#     order_status = models.CharField(
#         max_length=15,  # Increased length to accommodate "waiting_payment"
#         choices=ORDER_STATUS_CHOICES,
#         default='processing',
#     )
    
#     def save(self, *args, **kwargs):
#         # If the payment status is pending, set order status to "waiting_payment"
#         if self.payment_status == self.PENDING:
#             self.order_status = 'proceed_to_pay'  # Fixed capitalization to match choices
#         super().save(*args, **kwargs)
    
#     def __str__(self):
#         return self.title
    
# class ServiceFile(models.Model):
#     # Files linked to the Service (order)
#     service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="files")
#     file = models.FileField(upload_to="service_files/")
#     uploaded_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return f"{self.service.title} - {self.file.name}"