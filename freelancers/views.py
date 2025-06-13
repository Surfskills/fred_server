
import django_filters
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Sum
from django.db.models import Avg 
from uni_services.models import BaseService, Freelancer
from django.db.models import Sum, Count, Avg
from datetime import  timedelta
from django.utils import timezone
from django.db.models import Prefetch
from payouts.models import Payout, PayoutSetting

from .serializers import (
    FreelancerSerializer,
    FreelancerDetailSerializer,
    FreelancerCreateSerializer,
    FreelancerUpdateSerializer,
    FreelancerPortfolioSerializer,
    FreelancerReviewSerializer,
    FreelancerCertificationSerializer,
    FreelancerStatsSerializer,
    FreelancerStatusUpdateSerializer,
    FreelancerSearchSerializer
)

class FreelancerFilter(django_filters.FilterSet):
    min_rating = django_filters.NumberFilter(field_name='average_rating', lookup_expr='gte')
    max_rate = django_filters.NumberFilter(field_name='hourly_rate', lookup_expr='lte')
    min_projects = django_filters.NumberFilter(field_name='total_projects_completed', lookup_expr='gte')
    available = django_filters.BooleanFilter(field_name='is_available')
    
    class Meta:
        model = Freelancer
        fields = [
            'freelancer_type', 
            'experience_level', 
            'availability_status',
            'location',
            'is_profile_verified'
        ]

class FreelancerViewSet(viewsets.ModelViewSet):
    queryset = Freelancer.objects.select_related('user').prefetch_related(
        'portfolio_items', 
        'reviews',
        'certifications'
    ).all()
    serializer_class = FreelancerSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = FreelancerFilter
    search_fields = [
        'display_name', 
        'title', 
        'bio', 
        'skills', 
        'specializations',
        'user__email'
    ]
    ordering_fields = [
        'average_rating', 
        'hourly_rate', 
        'total_projects_completed',
        'created_at',
        'last_active'
    ]
    ordering = ['-average_rating']

    def get_serializer_class(self):
        if self.action == 'create':
            return FreelancerCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return FreelancerUpdateSerializer
        elif self.action == 'retrieve':
            return FreelancerDetailSerializer
        elif self.action == 'update_status':
            return FreelancerStatusUpdateSerializer
        elif self.action == 'search':
            return FreelancerSearchSerializer
        return super().get_serializer_class()

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'toggle_verification']:
            self.permission_classes = [IsAdminUser]
        elif self.action in ['my_profile']:
            self.permission_classes = [IsAuthenticated]
        return super().get_permissions()

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # For non-admin users, only show available freelancers
        if not self.request.user.is_staff:
            queryset = queryset.filter(is_available=True)
            
        # Handle search by skill
        skill = self.request.query_params.get('skill')
        if skill:
            queryset = queryset.filter(skills__contains=[skill.lower()])
            
        # Handle search by specialization
        specialization = self.request.query_params.get('specialization')
        if specialization:
            queryset = queryset.filter(specializations__contains=[specialization.lower()])
            
        # Handle location search
        location = self.request.query_params.get('location')
        if location:
            queryset = queryset.filter(location__icontains=location)
            
        return queryset

    @action(detail=False, methods=['get'])
    def my_profile(self, request):
        """Get the freelancer profile for the current user"""
        try:
            freelancer = request.user.freelancer_profile
            serializer = self.get_serializer(freelancer)
            return Response(serializer.data)
        except Freelancer.DoesNotExist:
            return Response(
                {'error': 'Freelancer profile not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['get'])
    def search(self, request):
        """Custom search endpoint with more flexible filtering"""
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        
        queryset = self.filter_queryset(self.get_queryset())
        
        # Apply additional filters from the search serializer
        data = serializer.validated_data
        
        if data.get('query'):
            queryset = queryset.filter(
                Q(display_name__icontains=data['query']) |
                Q(title__icontains=data['query']) |
                Q(bio__icontains=data['query']) |
                Q(skills__contains=[data['query'].lower()]) |
                Q(specializations__contains=[data['query'].lower()])
            )
            
        if data.get('freelancer_types'):
            queryset = queryset.filter(freelancer_type__in=data['freelancer_types'])
            
        if data.get('min_rating'):
            queryset = queryset.filter(average_rating__gte=data['min_rating'])
            
        if data.get('max_rate'):
            queryset = queryset.filter(hourly_rate__lte=data['max_rate'])
            
        if data.get('min_projects'):
            queryset = queryset.filter(total_projects_completed__gte=data['min_projects'])
            
        if data.get('available_only'):
            queryset = queryset.filter(is_available=True)
            
        if data.get('verified_only'):
            queryset = queryset.filter(is_profile_verified=True)
            
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = FreelancerSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
            
        serializer = FreelancerSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['patch'])
    def update_status(self, request, pk=None):
        """Update freelancer availability status"""
        freelancer = self.get_object()
        serializer = self.get_serializer(freelancer, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return Response(FreelancerSerializer(freelancer, context={'request': request}).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def toggle_availability(self, request, pk=None):
        """Toggle freelancer availability"""
        freelancer = self.get_object()
        freelancer.is_available = not freelancer.is_available
        freelancer.save()
        
        status_text = "available" if freelancer.is_available else "unavailable"
        return Response({
            'message': f'Freelancer marked as {status_text}',
            'freelancer': FreelancerSerializer(freelancer, context={'request': request}).data
        })

    @action(detail=True, methods=['post'])
    def toggle_verification(self, request, pk=None):
        """Toggle profile verification status"""
        freelancer = self.get_object()
        freelancer.is_profile_verified = not freelancer.is_profile_verified
        freelancer.save()
        
        status_text = "verified" if freelancer.is_profile_verified else "unverified"
        return Response({
            'message': f'Freelancer profile {status_text}',
            'freelancer': FreelancerSerializer(freelancer, context={'request': request}).data
        })

    @action(detail=True, methods=['get'])
    def portfolio(self, request, pk=None):
        """Get freelancer portfolio items"""
        freelancer = self.get_object()
        portfolio_items = freelancer.portfolio_items.all()
        serializer = FreelancerPortfolioSerializer(
            portfolio_items, 
            many=True, 
            context={'request': request}
        )
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def reviews(self, request, pk=None):
        """Get freelancer reviews"""
        freelancer = self.get_object()
        reviews = freelancer.reviews.all()
        serializer = FreelancerReviewSerializer(
            reviews, 
            many=True, 
            context={'request': request}
        )
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def certifications(self, request, pk=None):
        """Get freelancer certifications"""
        freelancer = self.get_object()
        certifications = freelancer.certifications.all()
        serializer = FreelancerCertificationSerializer(
            certifications, 
            many=True, 
            context={'request': request}
        )
        return Response(serializer.data)
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get freelancer statistics"""
        queryset = self.filter_queryset(self.get_queryset())
        
        stats = {
            'total_freelancers': queryset.count(),
            'available_freelancers': queryset.filter(is_available=True).count(),
            'busy_freelancers': queryset.filter(is_available=False).count(),
            'verified_freelancers': queryset.filter(is_profile_verified=True).count(),
            'average_rating': queryset.aggregate(
                avg_rating=Avg('average_rating')  # Changed from models.Avg to Avg
            )['avg_rating'] or 0,
            'average_rate': queryset.aggregate(
                avg_rate=Avg('hourly_rate')       # Changed from models.Avg to Avg
            )['avg_rate'] or 0,
            'freelancers_by_type': {
                item['freelancer_type']: item['count']
                for item in queryset.values('freelancer_type').annotate(
                    count=Count('id')
                )
            },
            'freelancers_by_experience': {
                item['experience_level']: item['count']
                for item in queryset.values('experience_level').annotate(
                    count=Count('id')
                )
            }
        }
        
        serializer = FreelancerStatsSerializer(stats)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def top_rated(self, request):
        """Get top rated freelancers"""
        queryset = self.filter_queryset(self.get_queryset())
        top_freelancers = queryset.order_by('-average_rating')[:10]
        serializer = FreelancerSerializer(
            top_freelancers, 
            many=True, 
            context={'request': request}
        )
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def recently_joined(self, request):
        """Get recently joined freelancers"""
        queryset = self.filter_queryset(self.get_queryset())
        recent_freelancers = queryset.order_by('-created_at')[:10]
        serializer = FreelancerSerializer(
            recent_freelancers, 
            many=True, 
            context={'request': request}
        )
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def add_portfolio_item(self, request, pk=None):
        """Add a portfolio item to freelancer"""
        freelancer = self.get_object()
        serializer = FreelancerPortfolioSerializer(
            data=request.data, 
            context={'request': request}
        )
        
        if serializer.is_valid():
            serializer.save(freelancer=freelancer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def add_review(self, request, pk=None):
        """Add a review for freelancer"""
        freelancer = self.get_object()
        
        # Check if user has already reviewed this freelancer
        existing_review = freelancer.reviews.filter(client=request.user).first()
        if existing_review:
            return Response(
                {'error': 'You have already reviewed this freelancer'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        serializer = FreelancerReviewSerializer(
            data=request.data, 
            context={'request': request}
        )
        
        if serializer.is_valid():
            serializer.save(freelancer=freelancer, client=request.user)
            
            # Update freelancer stats
            freelancer.update_statistics()
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def add_certification(self, request, pk=None):
        """Add a certification for freelancer"""
        freelancer = self.get_object()
        serializer = FreelancerCertificationSerializer(
            data=request.data, 
            context={'request': request}
        )
        
        if serializer.is_valid():
            serializer.save(freelancer=freelancer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def calculate_profile_completion(self, request, pk=None):
        """Calculate and update profile completion score"""
        freelancer = self.get_object()
        score = freelancer.calculate_profile_completion()
        return Response({
            'profile_completion_score': score,
            'freelancer': FreelancerSerializer(freelancer, context={'request': request}).data
        })

    @action(detail=True, methods=['get'])
    def similar(self, request, pk=None):
        """Get similar freelancers based on skills and type"""
        freelancer = self.get_object()
        
        # Get freelancers with similar skills and type, excluding current one
        similar_freelancers = Freelancer.objects.filter(
            Q(freelancer_type=freelancer.freelancer_type) |
            Q(skills__overlap=freelancer.skills),
            is_available=True
        ).exclude(id=freelancer.id).distinct()[:5]
        
        serializer = FreelancerSerializer(
            similar_freelancers, 
            many=True, 
            context={'request': request}
        )
        return Response(serializer.data)
    @action(detail=False, methods=['get'], url_path='dashboard-stats')
    def dashboard_stats(self, request):
        """Get freelancer dashboard statistics for authenticated user"""
        try:
            # Start with basic query and add prefetch_related based on actual relationships
            freelancer = Freelancer.objects.select_related('user').prefetch_related(
                'assigned_orders',  # Remove the __order part that's causing the error
                'reviews',
                'portfolio_items',
                'certifications'
            ).get(user=request.user)
        except Freelancer.DoesNotExist:
            return Response(
                {'error': 'Freelancer profile not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Calculate time periods
        now = timezone.now()
        one_month_ago = now - timedelta(days=30)
        three_months_ago = now - timedelta(days=90)
        
        # Get assigned orders queryset
        assigned_orders = freelancer.assigned_orders.all()
        
        # Calculate monthly earnings safely
        try:
            monthly_earnings = assigned_orders.filter(
                status='completed',
                completed_at__gte=one_month_ago
            ).aggregate(
                total=Sum('bid_amount')
            )['total'] or 0
        except Exception as e:
            monthly_earnings = 0
        
        # Calculate quarterly earnings safely
        try:
            quarterly_earnings = assigned_orders.filter(
                status='completed',
                completed_at__gte=three_months_ago
            ).aggregate(
                total=Sum('bid_amount')
            )['total'] or 0
        except Exception as e:
            quarterly_earnings = 0
        
        # Safe count operations
        try:
            active_tasks = assigned_orders.filter(
                status__in=['assigned', 'start_working', 'in_progress']
            ).count()
        except:
            active_tasks = 0
        
        try:
            completed_tasks = assigned_orders.filter(status='completed').count()
        except:
            completed_tasks = 0
        
        try:
            pending_tasks = assigned_orders.filter(
                status__in=['submitted', 'under_review']
            ).count()
        except:
            pending_tasks = 0
        
        # Calculate success rate
        success_rate = self._calculate_success_rate(freelancer)
        
        # Get profile completion score safely
        try:
            profile_completion = freelancer.calculate_profile_completion()
        except:
            profile_completion = 50  # Default value
        
        # Build response data
        stats = {
            # Financial stats
            'financial': {
                'total_earnings': float(freelancer.total_earnings or 0),
                'monthly_earnings': float(monthly_earnings),
                'quarterly_earnings': float(quarterly_earnings),
                'average_project_value': self._calculate_average_project_value(freelancer),
                'earnings_growth': self._calculate_earnings_growth(freelancer),
            },
            
            # Task/Project stats
            'projects': {
                'active_tasks': active_tasks,
                'completed_tasks': completed_tasks,
                'pending_tasks': pending_tasks,
                'total_projects': freelancer.total_projects_completed or 0,
                'success_rate': success_rate,
                'completion_rate': self._calculate_completion_rate(freelancer),
            },
            
            # Profile stats
            'profile': {
                'average_rating': float(freelancer.average_rating or 0),
                'total_reviews': freelancer.reviews.count(),
                'profile_completion': profile_completion,
                'profile_views': getattr(freelancer, 'profile_views', 0),
                'is_verified': freelancer.is_profile_verified,
                'portfolio_items': freelancer.portfolio_items.count(),
                'certifications': freelancer.certifications.count(),
            },
            
            # Activity stats
            'activity': {
                'last_active': freelancer.last_active,
                'join_date': freelancer.created_at,
                'days_active': (now - freelancer.created_at).days,
                'is_available': freelancer.is_available,
                'availability_status': getattr(freelancer, 'availability_status', 'available'),
            },
            
            # Chart data
            'charts': {
                'earnings_data': self._get_earnings_data(freelancer),
                'task_status_data': self._get_task_status_data(freelancer),
                'rating_trend': self._get_rating_trend(freelancer),
            },
            
            # Recent activity
            'recent_activity': self._get_recent_activity(freelancer),
            
            # Performance metrics
            'performance': {
                'response_time': self._calculate_avg_response_time(freelancer),
                'project_delivery_time': self._calculate_avg_delivery_time(freelancer),
                'client_satisfaction': self._calculate_client_satisfaction(freelancer),
                'repeat_client_rate': self._calculate_repeat_client_rate(freelancer),
            }
        }
        
        return Response(stats)

    def _calculate_success_rate(self, freelancer):
        """Calculate success rate based on completed vs cancelled/failed projects"""
        completed = freelancer.assigned_orders.filter(status='completed').count()
        cancelled = freelancer.assigned_orders.filter(
            status__in=['cancelled', 'failed', 'disputed']
        ).count()
        total = completed + cancelled
        
        if total == 0:
            return 100  # Default to 100% if no projects
        
        return round((completed / total) * 100, 1)

    def _calculate_completion_rate(self, freelancer):
        """Calculate project completion rate"""
        total_assigned = freelancer.assigned_orders.count()
        completed = freelancer.assigned_orders.filter(status='completed').count()
        
        if total_assigned == 0:
            return 100
        
        return round((completed / total_assigned) * 100, 1)

    def _calculate_average_project_value(self, freelancer):
        """Calculate average project value"""
        avg_value = freelancer.assigned_orders.filter(
            status='completed',
            bid_amount__isnull=False
        ).aggregate(
            avg=Avg('bid_amount')
        )['avg']
        
        return float(avg_value or 0)

    def _calculate_earnings_growth(self, freelancer):
        """Calculate earnings growth compared to previous month"""
        now = timezone.now()
        current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_month_start = current_month_start - timedelta(days=32)
        last_month_start = last_month_start.replace(day=1)
        
        current_month_earnings = freelancer.assigned_orders.filter(
            status='completed',
            completed_at__gte=current_month_start
        ).aggregate(total=Sum('bid_amount'))['total'] or 0
        
        last_month_earnings = freelancer.assigned_orders.filter(
            status='completed',
            completed_at__gte=last_month_start,
            completed_at__lt=current_month_start
        ).aggregate(total=Sum('bid_amount'))['total'] or 0
        
        if last_month_earnings == 0:
            return 0 if current_month_earnings == 0 else 100
        
        growth = ((current_month_earnings - last_month_earnings) / last_month_earnings) * 100
        return round(growth, 1)

    def _get_earnings_data(self, freelancer):
        """Get earnings data for the last 6 months"""
        now = timezone.now()
        months = []
        
        for i in range(5, -1, -1):
            # Calculate month start
            month_date = now - timedelta(days=30*i)
            month_start = month_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            # Calculate next month start
            if month_start.month == 12:
                next_month = month_start.replace(year=month_start.year + 1, month=1)
            else:
                next_month = month_start.replace(month=month_start.month + 1)
            
            earnings = freelancer.assigned_orders.filter(
                status='completed',
                completed_at__gte=month_start,
                completed_at__lt=next_month
            ).aggregate(
                total=Sum('bid_amount')
            )['total'] or 0
            
            months.append({
                'month': month_start.strftime('%b %Y'),
                'earnings': float(earnings),
                'projects': freelancer.assigned_orders.filter(
                    status='completed',
                    completed_at__gte=month_start,
                    completed_at__lt=next_month
                ).count()
            })
        
        return months

    def _get_task_status_data(self, freelancer):
        """Get task status distribution"""
        status_counts = freelancer.assigned_orders.values('status').annotate(
            count=Count('id')
        )
        
        status_map = {
            'completed': {'name': 'Completed', 'color': '#10b981'},
            'in_progress': {'name': 'In Progress', 'color': '#3b82f6'},
            'start_working': {'name': 'To Start', 'color': '#f59e0b'},
            'assigned': {'name': 'Assigned', 'color': '#8b5cf6'},
            'on_hold': {'name': 'On Hold', 'color': '#64748b'},
            'submitted': {'name': 'Submitted', 'color': '#06b6d4'},
            'under_review': {'name': 'Under Review', 'color': '#84cc16'},
            'cancelled': {'name': 'Cancelled', 'color': '#ef4444'},
        }
        
        data = []
        for item in status_counts:
            if item['status'] in status_map:
                data.append({
                    'name': status_map[item['status']]['name'],
                    'value': item['count'],
                    'color': status_map[item['status']]['color']
                })
        
        return data

    def _get_rating_trend(self, freelancer):
        """Get rating trend over time"""
        reviews = freelancer.reviews.order_by('created_at')
        
        if not reviews.exists():
            return []
        
        trend = []
        running_total = 0
        count = 0
        
        for review in reviews:
            count += 1
            running_total += review.rating
            avg_rating = running_total / count
            
            trend.append({
                'date': review.created_at.strftime('%b %Y'),
                'rating': round(avg_rating, 2),
                'review_count': count
            })
        
        return trend

    def _get_recent_activity(self, freelancer):
        """Get recent activity for the freelancer"""
        activities = []
        
        # Get recent completed projects
        completed = freelancer.assigned_orders.filter(
            status='completed'
        ).order_by('-completed_at')[:3]
        
        for project in completed:
            activities.append({
                'id': f"project_{project.id}",
                'type': 'project_completed',
                'action': 'Completed project',
                'title': project.order.title if hasattr(project, 'order') else 'Project',
                'time': project.completed_at,
                'time_ago': self._time_ago(project.completed_at),
                'amount': f"${project.bid_amount}" if project.bid_amount else None,
                'icon': 'check-circle'
            })
        
        # Get recent reviews
        reviews = freelancer.reviews.order_by('-created_at')[:3]
        
        for review in reviews:
            activities.append({
                'id': f"review_{review.id}",
                'type': 'review_received',
                'action': 'Received review',
                'title': f"{review.rating} star review",
                'time': review.created_at,
                'time_ago': self._time_ago(review.created_at),
                'amount': f"{review.rating}/5 stars",
                'icon': 'star'
            })
        
        # Get recent project assignments
        assigned = freelancer.assigned_orders.filter(
            status='assigned'
        ).order_by('-created_at')[:2]
        
        for project in assigned:
            activities.append({
                'id': f"assigned_{project.id}",
                'type': 'project_assigned',
                'action': 'New project assigned',
                'title': project.order.title if hasattr(project, 'order') else 'New Project',
                'time': project.created_at,
                'time_ago': self._time_ago(project.created_at),
                'amount': f"${project.bid_amount}" if project.bid_amount else None,
                'icon': 'briefcase'
            })
        
        # Sort all activities by time (most recent first)
        activities.sort(key=lambda x: x['time'], reverse=True)
        
        return activities[:10]

    def _calculate_avg_response_time(self, freelancer):
        """Calculate average response time to new projects"""
        # This would require tracking when projects are posted vs when freelancer responds
        # For now, return a placeholder or implement based on your bid/message system
        return "< 2 hours"  # Placeholder

    def _calculate_avg_delivery_time(self, freelancer):
        """Calculate average project delivery time"""
        completed_orders = freelancer.assigned_orders.filter(
            status='completed',
            started_at__isnull=False,
            completed_at__isnull=False
        )
        
        if not completed_orders.exists():
            return 0
        
        total_hours = 0
        count = 0
        
        for order in completed_orders:
            if order.started_at and order.completed_at:
                duration = order.completed_at - order.started_at
                total_hours += duration.total_seconds() / 3600
                count += 1
        
        if count == 0:
            return 0
        
        avg_hours = total_hours / count
        
        if avg_hours < 24:
            return f"{round(avg_hours)} hours"
        else:
            return f"{round(avg_hours / 24)} days"

    def _calculate_client_satisfaction(self, freelancer):
        """Calculate overall client satisfaction percentage"""
        reviews = freelancer.reviews.all()
        
        if not reviews.exists():
            return 100  # Default to 100% if no reviews
        
        satisfied_reviews = reviews.filter(rating__gte=4).count()
        total_reviews = reviews.count()
        
        return round((satisfied_reviews / total_reviews) * 100, 1)

    def _calculate_repeat_client_rate(self, freelancer):
        """Calculate percentage of repeat clients"""
        orders = freelancer.assigned_orders.all()
        
        if not orders.exists():
            return 0
        
        # Count unique clients - adjust based on your actual model structure
        try:
            unique_clients = orders.values('client_id').distinct().count()
        except:
            # Fallback if client_id doesn't exist - adjust field name as needed
            unique_clients = orders.count()  # Temporary fallback
        total_orders = orders.count()
        
        if unique_clients == 0:
            return 0
        
        # If we have more orders than unique clients, we have repeat clients
        repeat_rate = max(0, (total_orders - unique_clients) / total_orders * 100)
        
        return round(repeat_rate, 1)

    def _time_ago(self, dt):
        """Convert datetime to time ago string"""
        if not dt:
            return "Unknown"
            
        now = timezone.now()
        diff = now - dt
        
        if diff.days > 7:
            return f"{diff.days // 7} weeks ago"
        elif diff.days > 0:
            return f"{diff.days} days ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hours ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minutes ago"
        else:
            return "Just now"
    @action(detail=True, methods=['get'])
    def full_profile(self, request, pk=None):
        """Get complete freelancer profile with payouts, tasks, and settings"""
        try:
            # Prefetch related data to optimize queries
            freelancer = Freelancer.objects.select_related(
                'user',
                'user__profile',  # Access profile through user
                'user__profile__payout_setting'  # Access payout_setting through profile
            ).prefetch_related(
                'portfolio_items',
                'reviews',
                'certifications',
                Prefetch(
                    'user__profile__payouts',  # Access payouts through profile
                    queryset=Payout.objects.select_related('partner', 'requested_by', 'processed_by')
                                        .order_by('-request_date')
                ),
                Prefetch(
                    'assigned_orders',
                    queryset=BaseService.objects.filter(status='completed')
                                        .order_by('-completed_at')
                )
            ).get(pk=pk)
        except Freelancer.DoesNotExist:
            return Response(
                {'error': 'Freelancer not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Serialize the base freelancer data
        freelancer_data = FreelancerDetailSerializer(freelancer, context={'request': request}).data

        # Get partner profile (could be None if not set up yet)
        partner_profile = getattr(freelancer.user, 'profile', None)
        
        # Add payouts data
        payouts_data = []
        total_earnings = 0
        pending_amount = 0
        
        if partner_profile:
            payouts = partner_profile.payouts.all()
            for payout in payouts:
                payouts_data.append({
                    'id': payout.id,
                    'amount': float(payout.amount),
                    'status': payout.status,
                    'payment_method': payout.payment_method,
                    'request_date': payout.request_date,
                    'processed_date': payout.processed_date,
                    'transaction_id': payout.transaction_id,
                    'note': payout.note,
                })
            
            # Calculate total earnings from payouts
            total_earnings = partner_profile.payouts.filter(status='completed').aggregate(
                total=Sum('amount')
            )['total'] or 0
            
            # Calculate pending amount
            pending_amount = partner_profile.payouts.filter(status='pending').aggregate(
                total=Sum('amount')
            )['total'] or 0

        # Add completed tasks data
        completed_tasks = freelancer.assigned_orders.all()
        tasks_data = []
        for task in completed_tasks:
            tasks_data.append({
                'id': task.id,
                'title': task.title,
                'service_type': task.service_type,
                'status': task.status,
                'cost': float(task.final_cost) if task.final_cost else None,
                'completed_at': task.completed_at,
            })

        # Add payout settings data
        payout_settings = {}
        if partner_profile and hasattr(partner_profile, 'payout_setting'):
            payout_setting = partner_profile.payout_setting
            payout_settings = {
                'payment_method': payout_setting.payment_method,
                'payment_details': payout_setting.payment_details,
                'minimum_payout_amount': float(payout_setting.minimum_payout_amount),
                'auto_payout': payout_setting.auto_payout,
                'payout_schedule': payout_setting.payout_schedule,
                'updated_at': payout_setting.updated_at,
            }

        # Build response data (moved outside the if block)
        response_data = {
            'freelancer': freelancer_data,
            'payouts': {
                'total_count': len(payouts_data),
                'completed_amount': float(total_earnings),
                'pending_amount': float(pending_amount),
                'list': payouts_data,
            },
            'tasks': {  
                'total_completed': completed_tasks.count(),
                'list': tasks_data,
            },
            'payout_settings': payout_settings,
            'stats': {
                'average_rating': freelancer.average_rating,
                'total_projects': freelancer.total_projects_completed,
                'profile_completion': freelancer.profile_completion_score,
            }
        }

        return Response(response_data)


    @action(detail=True, methods=['post'])
    def update_payout_settings(self, request, pk=None):
        """Update freelancer payout settings (admin only)"""
        freelancer = self.get_object()
        
        # Get or create partner profile
        partner_profile = getattr(freelancer.user, 'profile', None)
        if not partner_profile:
            # Create partner profile if it doesn't exist
            partner_profile = Profile.objects.create(user=freelancer.user)
        
        try:
            payout_setting = partner_profile.payout_setting
        except PayoutSetting.DoesNotExist:
            payout_setting = PayoutSetting(partner=partner_profile)

        serializer = PayoutSettingSerializer(payout_setting, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def earnings_report(self, request, pk=None):
        """Generate earnings report for freelancer (admin only)"""
        freelancer = self.get_object()
        
        # Get partner profile
        partner_profile = getattr(freelancer.user, 'profile', None)
        if not partner_profile:
            return Response(
                {'error': 'No partner profile found for this freelancer'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Generate report data
        earnings = partner_profile.earnings.all()
        payouts = partner_profile.payouts.all()
        
        report_data = {
            'partner_id': partner_profile.id,
            'partner_name': partner_profile.name,
            'total_earnings': earnings.aggregate(Sum('amount'))['amount__sum'] or 0,
            'total_paid': payouts.filter(status='completed').aggregate(Sum('amount'))['amount__sum'] or 0,
            'earnings_by_status': {
                'available': earnings.filter(status='available').aggregate(Sum('amount'))['amount__sum'] or 0,
                'processing': earnings.filter(status='processing').aggregate(Sum('amount'))['amount__sum'] or 0,
                'paid': earnings.filter(status='paid').aggregate(Sum('amount'))['amount__sum'] or 0,
            },
            'recent_earnings': earnings.order_by('-created_at')[:10].values(),
            'recent_payouts': payouts.order_by('-request_date')[:10].values(),
        }
        
        return Response(report_data)
    
