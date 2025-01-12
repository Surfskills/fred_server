# # authentication/signals.py
# from django.db.models.signals import post_save
# from django.dispatch import receiver
# from .models import User, Profile

# @receiver(post_save, sender=User)
# def create_user_profile(sender, instance, created, **kwargs):
#     """Create a profile when a new user is created."""
#     if created:
#         Profile.objects.create(user=instance)

# @receiver(post_save, sender=User)
# def save_user_profile(sender, instance, **kwargs):
#     """Save the user's profile when the user is saved."""
#     instance.profile.save()
