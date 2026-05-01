"""
Development seed: three demo freelancers (Native, Dynamic, Demers) for marketplace cards.

Usage:
  python manage.py seed_marketplace_freelancers

Default password for seeded accounts: DevSeed123!
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from uni_services.models import Freelancer, FreelancerPortfolio

User = get_user_model()

SEED_PASSWORD = 'DevSeed123!'

DEMO = [
    {
        'tier': 'native',
        'email': 'demo.native@gigshub.local',
        'first_name': 'Ada',
        'last_name': 'Mwangi',
        'display_name': 'Ada M.',
        'title': 'Product depth · selective partner intake · niche craft',
        'bio': (
            'Native on GigsHub — cleared selective gates coordinated with implementing partners; concentrates rare product '
            'skills in narrow lanes before catalog exposure.'
        ),
        'skills': ['Figma', 'Design systems', 'UX research'],
        'portfolio': ['Mobile banking UX', 'Design tokens library', 'Onboarding flows'],
    },
    {
        'tier': 'dynamic',
        'email': 'demo.dynamic@gigshub.local',
        'first_name': 'Marcus',
        'last_name': 'Chen',
        'display_name': 'Marcus C.',
        'title': 'Cloud & platform integrations (ex-big tech)',
        'bio': (
            'Dynamic — implementing-partner certification (WeDemo Africa) completed before claiming this tier; '
            'ex-hyperscale alum blending corporate depth with independent delivery.'
        ),
        'skills': ['Python', 'PostgreSQL', 'Kafka'],
        'portfolio': ['SAP connector', 'Event-driven payroll', 'Audit pipelines'],
    },
    {
        'tier': 'demer',
        'email': 'demo.demer@gigshub.local',
        'first_name': 'Sofia',
        'last_name': 'Reyes',
        'display_name': 'Sofia R.',
        'title': 'Strategy & architecture · private-practice technocrat',
        'bio': (
            'Demers — prerequisite certification from implementing partner satisfied; elite technocrat with historically '
            'private-practice work under strict senior access on GigsHub.'
        ),
        'skills': ['Program management', 'Technical writing', 'Stakeholder alignment'],
        'portfolio': ['Zero-downtime migration', 'Exec readouts', 'Vendor selection'],
    },
]


class Command(BaseCommand):
    help = 'Create three demo freelancer accounts (Native, Dynamic, Demers) for marketplace development.'

    def handle(self, *args, **options):
        for row in DEMO:
            user, created = User.objects.get_or_create(
                email=row['email'],
                defaults={
                    'first_name': row['first_name'],
                    'last_name': row['last_name'],
                    'user_type': User.Types.FREELANCER,
                },
            )
            if created:
                user.set_password(SEED_PASSWORD)
                user.save()
                self.stdout.write(self.style.SUCCESS(f'Created user {row["email"]}'))
            else:
                if user.user_type != User.Types.FREELANCER:
                    user.user_type = User.Types.FREELANCER
                    user.save(update_fields=['user_type'])
                self.stdout.write(f'User exists {row["email"]}, ensuring freelancer profile…')

            fl, fl_created = Freelancer.objects.get_or_create(
                user=user,
                defaults={
                    'display_name': row['display_name'],
                    'title': row['title'],
                    'bio': row['bio'],
                    'freelancer_type': 'other',
                    'skills': row['skills'],
                    'specializations': [],
                    'languages': [{'language': 'English', 'proficiency': 'Native'}],
                    'marketplace_tier': row['tier'],
                    'is_available': True,
                    'availability_status': 'available',
                    'hourly_rate': 75,
                    'average_rating': 4.8,
                    'total_projects_completed': 12,
                },
            )
            fl.display_name = row['display_name']
            fl.title = row['title']
            fl.bio = row['bio']
            fl.skills = row['skills']
            fl.marketplace_tier = row['tier']
            fl.is_available = True
            fl.save()

            for i, title in enumerate(row['portfolio']):
                FreelancerPortfolio.objects.get_or_create(
                    freelancer=fl,
                    title=title,
                    defaults={
                        'description': f'Catalog sample {i + 1} for {row["tier"]} tier demo.',
                        'is_featured': i == 0,
                    },
                )

            self.stdout.write(self.style.SUCCESS(f'  → Freelancer {fl.id} ({row["tier"]}) ready'))

        self.stdout.write(self.style.SUCCESS(f'Done. Password for all: {SEED_PASSWORD}'))
