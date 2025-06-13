# signals.py - Fixed version to prevent recursion

from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from authentication.models import User, Profile
from uni_services.models import Freelancer
from django.db import transaction
import threading

# Thread-local storage to track signal processing
_thread_locals = threading.local()

def get_signal_processing_flag(signal_name, instance_id):
    """Get signal processing flag for current thread"""
    if not hasattr(_thread_locals, 'processing'):
        _thread_locals.processing = set()
    return f"{signal_name}_{instance_id}" in _thread_locals.processing

def set_signal_processing_flag(signal_name, instance_id, value=True):
    """Set signal processing flag for current thread"""
    if not hasattr(_thread_locals, 'processing'):
        _thread_locals.processing = set()
    
    flag = f"{signal_name}_{instance_id}"
    if value:
        _thread_locals.processing.add(flag)
    else:
        _thread_locals.processing.discard(flag)


@receiver(pre_save, sender=User)
def track_user_type_changes(sender, instance, **kwargs):
    """Track user type changes for profile cleanup"""
    if instance.pk:  # Only for existing users
        try:
            original = User.objects.get(pk=instance.pk)
            instance._original_user_type = original.user_type
        except User.DoesNotExist:
            instance._original_user_type = None
    else:
        instance._original_user_type = None


@receiver(post_save, sender=User)
def handle_user_profiles(sender, instance, created, **kwargs):
    """Create related profiles when a user is created or user_type changes"""
    
    # Prevent recursion using thread-local flag
    signal_flag = f"user_post_save_{instance.pk}"
    if get_signal_processing_flag("user_post_save", instance.pk):
        return
    
    try:
        set_signal_processing_flag("user_post_save", instance.pk, True)
        
        # Always ensure basic Profile exists
        if created:
            Profile.objects.get_or_create(user=instance)
            print(f"Created basic profile for {instance.email}")
        
        # Handle freelancer profile creation
        if instance.user_type == User.Types.FREELANCER:
            freelancer_profile, freelancer_created = Freelancer.objects.get_or_create(
                user=instance,
                defaults={
                    'display_name': instance.display_name or '',
                    'bio': '',
                    'title': '',
                    'freelancer_type': 'other',
                    'skills': [],
                    'specializations': [],
                    'languages': [{"language": "English", "proficiency": "Native"}],
                    'location': '',
                    'timezone': '',
                }
            )
            if freelancer_created:
                print(f"Created freelancer profile for {instance.email}")
        
        # Handle user type changes - clean up profiles if user type changed
        elif hasattr(instance, '_original_user_type') and instance._original_user_type:
            original_type = instance._original_user_type
            if original_type == User.Types.FREELANCER and instance.user_type != User.Types.FREELANCER:
                # User changed from freelancer to something else
                try:
                    instance.freelancer_profile.delete()
                    print(f"Deleted freelancer profile for {instance.email}")
                except Freelancer.DoesNotExist:
                    pass
        
        # Defer profile completion calculation to avoid recursion
        if not created:
            # Use transaction.on_commit to defer the calculation
            transaction.on_commit(lambda: calculate_user_profile_completion_safe(instance.pk))
            
    finally:
        set_signal_processing_flag("user_post_save", instance.pk, False)


@receiver(post_save, sender=Freelancer)
def update_freelancer_completion(sender, instance, **kwargs):
    """Update profile completion when freelancer profile is updated"""
    
    # Prevent recursion
    if get_signal_processing_flag("freelancer_post_save", instance.pk):
        return
        
    try:
        set_signal_processing_flag("freelancer_post_save", instance.pk, True)
        
        if not kwargs.get('created', False):  # Only for updates, not creation
            # Defer calculations to avoid recursion
            transaction.on_commit(lambda: calculate_freelancer_profile_completion_safe(instance.pk))
            
    finally:
        set_signal_processing_flag("freelancer_post_save", instance.pk, False)


@receiver(post_delete, sender=Freelancer)
def cleanup_freelancer_deletion(sender, instance, **kwargs):
    """Handle cleanup when freelancer profile is deleted"""
    # Update user's profile completion after commit
    if instance.user:
        user_pk = instance.user.pk
        transaction.on_commit(lambda: calculate_user_profile_completion_safe(user_pk))
        print(f"Scheduled cleanup after freelancer profile deletion for {instance.user.email}")


def calculate_user_profile_completion_safe(user_pk):
    """Safely calculate user profile completion without triggering signals"""
    try:
        user = User.objects.get(pk=user_pk)
        
        # Prevent recursion
        if get_signal_processing_flag("profile_completion", user_pk):
            return
            
        try:
            set_signal_processing_flag("profile_completion", user_pk, True)
            
            completion = 0
            total_fields = 0
            
            # Basic fields (20% each)
            basic_fields = [
                user.first_name,
                user.last_name,
                user.phone_number,
                bool(user.profile_picture),
            ]
            
            for field in basic_fields:
                total_fields += 1
                if field:
                    completion += 1
            
            # Type-specific completion
            if user.is_freelancer:
                try:
                    freelancer_profile = user.freelancer_profile
                    if freelancer_profile:
                        freelancer_fields = [
                            bool(freelancer_profile.bio),
                            bool(freelancer_profile.hourly_rate),
                        ]
                        
                        for field in freelancer_fields:
                            total_fields += 1
                            if field:
                                completion += 1
                except Freelancer.DoesNotExist:
                    pass
            
            percentage = int((completion / total_fields) * 100) if total_fields > 0 else 0
            
            # Use bulk_update to avoid triggering signals
            User.objects.filter(pk=user_pk).update(
                profile_completion_percentage=percentage,
                is_profile_complete=percentage >= 80
            )
            
        finally:
            set_signal_processing_flag("profile_completion", user_pk, False)
            
    except User.DoesNotExist:
        pass
    except Exception as e:
        print(f"Error calculating user profile completion: {e}")


def calculate_freelancer_profile_completion_safe(freelancer_pk):
    """Safely calculate freelancer profile completion without triggering signals"""
    try:
        freelancer = Freelancer.objects.select_related('user').get(pk=freelancer_pk)
        
        # Prevent recursion
        if get_signal_processing_flag("freelancer_completion", freelancer_pk):
            return
            
        try:
            set_signal_processing_flag("freelancer_completion", freelancer_pk, True)
            
            # Calculate freelancer-specific completion
            freelancer.calculate_profile_completion()
            
            # Also update the user's overall profile completion
            if freelancer.user:
                calculate_user_profile_completion_safe(freelancer.user.pk)
                
        finally:
            set_signal_processing_flag("freelancer_completion", freelancer_pk, False)
            
    except Freelancer.DoesNotExist:
        pass
    except Exception as e:
        print(f"Error calculating freelancer profile completion: {e}")