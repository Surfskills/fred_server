from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django_filters.rest_framework import DjangoFilterBackend
from django_filters import rest_framework as django_filters
from django.db.models import Q, Count, Sum
from django.utils import timezone
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db.models import Avg
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count, Sum, Q, F, Avg
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import random
from authentication.models import User

# views.py
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from django.db.models import Sum, Avg, Count
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from .models import (
    BaseService, SoftwareService, ResearchService, CustomService, 
    ServiceFile, Freelancer, OrderStatusHistory, Bid
)
from .serializers import (
    BaseServiceSerializer, ServiceListSerializer, BaseServiceCreateSerializer,
    SoftwareServiceSerializer, SoftwareServiceCreateSerializer,
    ResearchServiceSerializer, ResearchServiceCreateSerializer,
    CustomServiceSerializer, CustomServiceCreateSerializer,
    OrderAssignmentSerializer, OrderStatusUpdateSerializer, 
    ServicePaymentUpdateSerializer, OrderActionSerializer,
    ServiceFileSerializer, ServiceFileUploadSerializer,

    OrderCommentSerializer, OrderCommentCreateSerializer,
    OrderStatusHistorySerializer, OrderStatsSerializer, 
   BidSerializer, BidCreateSerializer
)


# Updated Mixins for your custom User model
class BasePermissionMixin:
    """Handles common permission checks for your custom User model"""
    
    def check_freelancer_permission(self, request):
        """Check if user is a freelancer type"""
        if request.user.is_freelancer:
            # If you have a separate Freelancer model, get that profile
            # Otherwise, just return the user if they're a freelancer type
            try:
                return request.user.freelancer_profile  # If you have a related Freelancer model
            except AttributeError:
                return request.user  # If freelancer info is stored directly in User model
        return None

    def check_service_permission(self, request, service):
        if request.user.is_staff or request.user.is_admin:
            return True
        if service.user == request.user:
            return True
        
        # Check if user is a freelancer and assigned to this service
        if request.user.is_freelancer:
            # Assuming your BaseService model has an assigned_to field that references User
            if hasattr(service, 'assigned_to') and service.assigned_to == request.user:
                return True
        return False

class BaseServiceActionMixin:
    """Handles common service actions - Updated for your User model"""
    
    @action(detail=True, methods=['post'])
    def upload_file(self, request, pk=None):
        service = self.get_object()
        if not self.check_service_permission(request, service):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = ServiceFileUploadSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save(service=service, uploaded_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def files(self, request, pk=None):
        service = self.get_object()
        files = service.files.all()
        serializer = ServiceFileSerializer(files, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def add_comment(self, request, pk=None):
        order = self.get_object()
        if not self.check_service_permission(request, order):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = OrderCommentCreateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save(order=order, author=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


    @action(detail=True, methods=['get'])
    def comments(self, request, pk=None):
        order = self.get_object()
        comments = order.comments.all()
        if not request.user.is_staff:
            comments = comments.filter(is_internal=False)
        serializer = OrderCommentSerializer(comments, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        order = self.get_object()
        history = order.status_history.all()
        serializer = OrderStatusHistorySerializer(history, many=True, context={'request': request})
        return Response(serializer.data)

# Filter classes
class BaseServiceFilter(django_filters.FilterSet):
    service_type = django_filters.CharFilter(field_name='service_type')
    status = django_filters.CharFilter(field_name='status') 
    payment_status = django_filters.CharFilter(field_name='payment_status')
    order_status = django_filters.CharFilter(field_name='order_status')
    acceptance_status = django_filters.CharFilter(field_name='acceptance_status')
    priority = django_filters.CharFilter(field_name='priority')
    user = django_filters.NumberFilter(field_name='user__id')
    assigned_to = django_filters.CharFilter(field_name='assigned_to__id')
    is_overdue = django_filters.BooleanFilter(method='filter_overdue')
    
    class Meta:
        model = BaseService
        fields = ['service_type', 'status', 'payment_status', 'order_status', 'acceptance_status', 'priority']

    def filter_overdue(self, queryset, name, value):
        if value:
            return queryset.filter(deadline__lt=timezone.now()).exclude(status__in=['completed', 'cancelled'])
        return queryset

class BidFilter(django_filters.FilterSet):
    status = django_filters.CharFilter(field_name='status')
    freelancer = django_filters.CharFilter(field_name='freelancer__id')
    order = django_filters.CharFilter(field_name='order__id')
    
    class Meta:
        model = Bid
        fields = ['status', 'freelancer', 'order']

# Complete Updated ViewSet
class BaseServiceViewSet(BasePermissionMixin, BaseServiceActionMixin, viewsets.ModelViewSet):
    queryset = BaseService.objects.select_related('user', 'assigned_to').prefetch_related('files', 'bids', 'comments')
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description', 'user__username', 'user__email', 'id']
    ordering_fields = ['created_at', 'updated_at', 'cost', 'title', 'deadline', 'priority']
    ordering = ['-created_at']

    def get_serializer_class(self):
        # Check if detailed view is requested via query param or for retrieve action
        detailed_view = (
            self.request.query_params.get('detailed', '').lower() == 'true'
            or self.action == 'retrieve'
        )
        
        serializer_map = {
            'list': BaseServiceSerializer if detailed_view else ServiceListSerializer,
            'create': self.get_create_serializer(),
            'assign_freelancer': OrderAssignmentSerializer,
            'reassign_freelancer': OrderAssignmentSerializer,
            'update_status': OrderStatusUpdateSerializer,
            'update_payment': ServicePaymentUpdateSerializer,
            'perform_action': OrderActionSerializer,
            'retrieve': BaseServiceSerializer,  # Always use full serializer for single item
        }
        
        # Default to BaseServiceSerializer for all other actions
        return serializer_map.get(self.action, BaseServiceSerializer)

    def get_create_serializer(self):
        service_type = self.request.data.get('service_type', '')
        create_serializers = {
            'software': SoftwareServiceCreateSerializer,
            'development': SoftwareServiceCreateSerializer,
            'research': ResearchServiceCreateSerializer,
            'writing': ResearchServiceCreateSerializer,
            'custom': CustomServiceCreateSerializer,
        }
        return create_serializers.get(service_type, BaseServiceCreateSerializer)

    def get_queryset(self):
        """
        Enhanced queryset with comprehensive filtering
        """
        queryset = BaseService.objects.select_related('user', 'assigned_to').prefetch_related('files', 'bids', 'comments')
        
        # Handle assigned_to_me parameter for freelancers
        assigned_to_me = self.request.query_params.get('assigned_to_me', None)
        if assigned_to_me and assigned_to_me.lower() == 'true':
            if self.request.user.is_authenticated and self.request.user.is_freelancer:
                try:
                    freelancer = Freelancer.objects.get(user=self.request.user)
                    queryset = queryset.filter(assigned_to=freelancer)
                except Freelancer.DoesNotExist:
                    # Return empty queryset if freelancer profile doesn't exist
                    queryset = queryset.none()
            else:
                # Return empty queryset if user is not a freelancer
                queryset = queryset.none()
        else:
            # Apply base permission filtering when not using assigned_to_me
            # Admin and staff can see all
            if self.request.user.is_staff or self.request.user.is_admin:
                pass  # No filtering needed
            elif self.request.user.is_freelancer:
                # Freelancer can see their assigned tasks and available tasks for bidding
                queryset = queryset.filter(
                    Q(user=self.request.user) | 
                    Q(assigned_to__user=self.request.user) |  # Updated to handle Freelancer model
                    Q(status='available')  # Available for bidding
                ).distinct()
            else:
                # Regular clients can only see their own services
                queryset = queryset.filter(user=self.request.user)
        
        # Handle status filtering
        status_param = self.request.query_params.get('status', None)
        if status_param:
            queryset = queryset.filter(status=status_param)
        
        # Handle service_type filtering
        service_type = self.request.query_params.get('service_type', None)
        if service_type:
            queryset = queryset.filter(service_type=service_type)
        
        # Handle freelancer filtering (for admin views)
        freelancer_id = self.request.query_params.get('freelancer', None)
        if freelancer_id:
            try:
                freelancer = Freelancer.objects.get(id=freelancer_id)
                queryset = queryset.filter(assigned_to=freelancer)
            except Freelancer.DoesNotExist:
                queryset = queryset.none()
        
        # Handle payment_status filtering
        payment_status = self.request.query_params.get('payment_status', None)
        if payment_status:
            queryset = queryset.filter(payment_status=payment_status)
        
        # Handle order_status filtering
        order_status = self.request.query_params.get('order_status', None)
        if order_status:
            queryset = queryset.filter(order_status=order_status)
        
        # Handle priority filtering
        priority = self.request.query_params.get('priority', None)
        if priority:
            queryset = queryset.filter(priority=priority)
        
        # Handle overdue filtering
        is_overdue = self.request.query_params.get('is_overdue', None)
        if is_overdue and is_overdue.lower() == 'true':
            queryset = queryset.filter(
                deadline__lt=timezone.now()
            ).exclude(status__in=['completed', 'cancelled'])
        
        return queryset

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def create(self, request, *args, **kwargs):
        if not request.data.get('service_type'):
            return Response({'service_type': ['This field is required.']}, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save(user=request.user)
        
        return_serializer = BaseServiceSerializer(instance, context={'request': request})
        headers = self.get_success_headers(serializer.data)
        return Response(return_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    # Admin Actions
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def assign_freelancer(self, request, pk=None):
        order = self.get_object()
        serializer = OrderAssignmentSerializer(data=request.data)
        
        if serializer.is_valid():
            freelancer_id = serializer.validated_data['freelancer_id']
            notes = serializer.validated_data.get('notes', '')
            
            try:
                freelancer = Freelancer.objects.get(id=freelancer_id)
                order.assign_to_freelancer(freelancer)
                order.status = 'assigned'
                order.save()
                
                OrderStatusHistory.objects.create(
                    order=order,
                    previous_status='available',
                    new_status='assigned',
                    changed_by=request.user,
                    notes=f"Assigned to {freelancer.name}. {notes}. Freelancer needs to start work.".strip()
                )
                
                return Response({
                    'message': f'Order assigned to {freelancer.name}. Freelancer can now start work.',
                    'order': BaseServiceSerializer(order, context={'request': request}).data
                })
            except Freelancer.DoesNotExist:
                return Response({'error': 'Freelancer not found'}, status=status.HTTP_404_NOT_FOUND)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def perform_action(self, request, pk=None):
        order = self.get_object()
        serializer = OrderActionSerializer(data=request.data)
        
        if serializer.is_valid():
            action = serializer.validated_data['action']
            freelancer_id = serializer.validated_data.get('freelancer_id')
            notes = serializer.validated_data.get('notes', '')
            old_status = order.status
            
            if action in ['assign', 'reassign']:
                freelancer = Freelancer.objects.get(id=freelancer_id)
                order.assign_to_freelancer(freelancer)
                order.status = 'start_working'  # Changed from 'assigned' to 'start_working'
                message = f'Order {action}ed to {freelancer.name}. Freelancer can start work immediately.'
            elif action == 'make_available':
                order.make_available()
                message = 'Order made available'
            elif action == 'put_on_hold':
                order.put_on_hold()
                message = 'Order put on hold'
            elif action == 'cancel':
                order.cancel_order()
                message = 'Order cancelled'
            elif action == 'start_progress':
                if order.status in ['assigned', 'start_working']:  # Accept both statuses
                    order.status = 'in_progress'
                    order.started_at = timezone.now()
                    order.save()
                    message = 'Order started'
                else:
                    return Response(
                        {'error': f'Cannot start progress from status: {order.status}. Order must be assigned first.'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            elif action == 'complete':
                order.complete_order()
                order.completed_at = timezone.now()
                message = 'Order completed'
            
            OrderStatusHistory.objects.create(
                order=order,
                previous_status=old_status,
                new_status=order.status,
                changed_by=request.user,
                notes=f"{message}. {notes}".strip()
            )
            
            return Response({
                'message': message,
                'order': BaseServiceSerializer(order, context={'request': request}).data
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    @action(detail=True, methods=['patch'])
    def update_status(self, request, pk=None):
        order = self.get_object()
        serializer = OrderStatusUpdateSerializer(order, data=request.data, partial=True, context={'request': request})
        
        if serializer.is_valid():
            serializer.save()
            return Response(BaseServiceSerializer(order, context={'request': request}).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['patch'])
    def update_payment(self, request, pk=None):
        order = self.get_object()
        serializer = ServicePaymentUpdateSerializer(order, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return Response(BaseServiceSerializer(order, context={'request': request}).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # Bidding System

    @action(detail=True, methods=['post'])
    def place_bid(self, request, pk=None):
        order = self.get_object()
        
        if not request.user.is_freelancer:
            return Response(
                {'error': 'You must be a freelancer to place bids'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        if order.status != 'available':
            return Response(
                {'error': 'This order is not available for bidding'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get the freelancer instance for the current user
        try:
            freelancer = Freelancer.objects.get(user=request.user)
        except Freelancer.DoesNotExist:
            return Response(
                {'error': 'Freelancer profile not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if freelancer has already placed a bid - use freelancer instance instead of user
        if order.bids.filter(freelancer=freelancer).exists():
            return Response(
                {'error': 'You have already placed a bid on this order'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = BidCreateSerializer(data=request.data, context={'request': request, 'order': order})
        if serializer.is_valid():
            bid = serializer.save(freelancer=freelancer)  # Use freelancer instance
            return Response(BidSerializer(bid, context={'request': request}).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    @action(detail=True, methods=['get'])
    def bids(self, request, pk=None):
        if not request.user.is_staff:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        order = self.get_object()
        bids = order.bids.all()
        serializer = BidSerializer(bids, many=True, context={'request': request})
        return Response(serializer.data)
    

    # In views.py - BaseServiceViewSet
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def approve_bid(self, request, pk=None):
        order = self.get_object()
        bid_id = request.data.get('bid_id')
        
        if not bid_id:
            return Response({'error': 'bid_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            bid = order.bids.get(id=bid_id, status='pending')
            bid.status = 'approved'
            bid.approved_by = request.user
            bid.approved_at = timezone.now()
            bid.save()
            
            # Reject all other pending bids for this order
            order.bids.filter(status='pending').exclude(id=bid_id).update(status='rejected')
            
            # Assign order to freelancer and set to 'start_working' status
            order.assign_to_freelancer(bid.freelancer)
            order.bid_amount = bid.bid_amount  # Explicitly update the bid_amount
            order.estimated_hours = bid.estimated_hours
            order.status = 'start_working'
            order.save()
            
            OrderStatusHistory.objects.create(
                order=order,
                previous_status='available',
                new_status='start_working',
                changed_by=request.user,
                notes=f"Bid approved and assigned to {bid.freelancer.name}. Bid amount: ${bid.bid_amount}. Freelancer can start work immediately."
            )
            
            return Response({
                'message': f'Bid approved and order assigned to {bid.freelancer.name}. Freelancer can start work immediately.',
                'order': BaseServiceSerializer(order, context={'request': request}).data,
                'bid': BidSerializer(bid, context={'request': request}).data
            })
            
        except Bid.DoesNotExist:
            return Response(
                {'error': 'Bid not found or already processed'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    # Also fix the freelancer work action methods
    @action(detail=True, methods=['post'])
    def start_work(self, request, pk=None):
        """Freelancer starts working on assigned task"""
        # Get the object with all related data
        order = self.get_queryset().select_related('user', 'assigned_to').prefetch_related('files', 'bids', 'comments').get(pk=pk)

        if order.status not in ['assigned', 'start_working']:
            return Response(
                {'error': f'Cannot start work from status: {order.status}. Order must be assigned first.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not request.user.is_freelancer:
            return Response(
                {'error': 'You are not a freelancer'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            freelancer = Freelancer.objects.get(user=request.user)
        except Freelancer.DoesNotExist:
            return Response(
                {'error': 'Freelancer profile not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        if order.assigned_to != freelancer:
            return Response(
                {'error': 'You are not assigned to this order'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        previous_status = order.status
        order.status = 'in_progress'
        order.started_at = timezone.now()
        order.save()
        
        OrderStatusHistory.objects.create(
            order=order,
            previous_status=previous_status,
            new_status='in_progress',
            changed_by=request.user,
            notes=f"Work started by {request.user.full_name or request.user.email}"
        )
        
        # Use BaseServiceSerializer for detailed response
        serializer = BaseServiceSerializer(order, context={'request': request})
        return Response({
            'message': 'Work started successfully',
            'order': serializer.data
        })

    @action(detail=True, methods=['post'])
    def submit_work(self, request, pk=None):
        """Freelancer submits completed work"""
        order = self.get_queryset().select_related('user', 'assigned_to').prefetch_related('files', 'bids', 'comments').get(pk=pk)

        if not request.user.is_freelancer:
            return Response(
                {'error': 'You are not a freelancer'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            freelancer = Freelancer.objects.get(user=request.user)
        except Freelancer.DoesNotExist:
            return Response(
                {'error': 'Freelancer profile not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        if order.assigned_to != freelancer:
            return Response(
                {'error': 'You are not assigned to this order'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        if order.status != 'in_progress':
            return Response(
                {'error': 'Order is not in progress'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if request.data.get('actual_hours'):
            order.actual_hours = request.data['actual_hours']
        
        if request.data.get('delivery_notes'):
            order.delivery_notes = request.data['delivery_notes']
        
        order.complete_order()
        order.completed_at = timezone.now()
        order.save()
        
        OrderStatusHistory.objects.create(
            order=order,
            previous_status='in_progress',
            new_status='completed',
            changed_by=request.user,
            notes=f"Work completed by {request.user.full_name or request.user.email}"
        )
        
        # Use BaseServiceSerializer for detailed response
        serializer = BaseServiceSerializer(order, context={'request': request})
        return Response({
            'message': 'Work submitted successfully. Order completed.',
            'order': serializer.data
        })
    # Dashboard/Stats Actions
    @action(detail=False, methods=['get'], permission_classes=[IsAdminUser])
    def stats(self, request):
        queryset = self.get_queryset()
        
        stats_data = {
            'total_orders': queryset.count(),
            'available_orders': queryset.filter(status='available').count(),
            'assigned_orders': queryset.filter(status='assigned').count(),
            'in_progress_orders': queryset.filter(status='in_progress').count(),
            'completed_orders': queryset.filter(status='completed').count(),
            'cancelled_orders': queryset.filter(status='cancelled').count(),
            'on_hold_orders': queryset.filter(status='on_hold').count(),
            'overdue_orders': queryset.filter(
                deadline__lt=timezone.now()
            ).exclude(status__in=['completed', 'cancelled']).count(),
            'total_revenue': queryset.filter(
                status='completed', 
                payment_status='paid'
            ).aggregate(Sum('cost'))['cost__sum'] or Decimal('0.00'),
            'pending_payment': queryset.filter(
                status='completed', 
                payment_status='pending'
            ).aggregate(Sum('cost'))['cost__sum'] or Decimal('0.00'),
        }
        
        serializer = OrderStatsSerializer(stats_data)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def assigned_to_me(self, request):
        """Get all tasks assigned to freelancer (both ready to start and in progress)"""
        if not request.user.is_freelancer:
            return Response(
                {'error': 'You are not a freelancer'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            # Get the freelancer instance associated with this user
            freelancer = Freelancer.objects.get(user=request.user)
        except Freelancer.DoesNotExist:
            return Response(
                {'error': 'Freelancer profile not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Filter by the freelancer instance
        queryset = self.get_queryset().filter(
            assigned_to=freelancer,  # Use freelancer instance
            status__in=['assigned', 'start_working', 'in_progress']
        )
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = ServiceListSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        
        serializer = ServiceListSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def tasks_to_start(self, request):
            """Get tasks assigned to freelancer that are ready to start"""
            
            # Check if user is authenticated
            if not request.user.is_authenticated:
                return Response(
                    {'error': 'Authentication required'}, 
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Check if user is a freelancer
            if not request.user.is_freelancer:
                return Response(
                    {'error': 'You are not a freelancer'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            try:
                # Get the freelancer instance associated with this user
                try:
                    freelancer = Freelancer.objects.get(user=request.user)
                except Freelancer.DoesNotExist:
                    return Response(
                        {'error': 'Freelancer profile not found'}, 
                        status=status.HTTP_404_NOT_FOUND
                    )
                
                # Filter by the freelancer instance, not the user
                queryset = self.get_queryset().filter(
                    assigned_to=freelancer,  # Use freelancer instance
                    status='start_working'
                )
                
                page = self.paginate_queryset(queryset)
                if page is not None:
                    serializer = ServiceListSerializer(page, many=True, context={'request': request})
                    return self.get_paginated_response(serializer.data)
                
                serializer = ServiceListSerializer(queryset, many=True, context={'request': request})
                return Response(serializer.data)
                
            except Exception as e:
                print(f"Error in tasks_to_start: {e}")
                return Response(
                    {'error': 'Unable to fetch tasks'}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

    @action(detail=False, methods=['get'])
    def tasks_in_progress(self, request):
        """Get tasks that freelancer is currently working on"""
        if not request.user.is_freelancer:
            return Response(
                {'error': 'You are not a freelancer'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            freelancer = Freelancer.objects.get(user=request.user)
        except Freelancer.DoesNotExist:
            return Response(
                {'error': 'Freelancer profile not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        queryset = self.get_queryset().filter(
            assigned_to=freelancer,
            status='in_progress'
        ).select_related('user', 'assigned_to').prefetch_related('files', 'bids', 'comments')
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = ServiceListSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        
        serializer = ServiceListSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)
    @action(detail=False, methods=['get'])
    def ready_to_start(self, request):
        """Alias for tasks_to_start - for backward compatibility"""
        return self.tasks_to_start(request)


    @action(detail=False, methods=['get'])
    def available_for_bidding(self, request):
        """Get available tasks for freelancer to bid on"""
        if not request.user.is_freelancer:
            return Response(
                {'error': 'You are not a freelancer'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            # Get the freelancer instance associated with this user
            freelancer = Freelancer.objects.get(user=request.user)
        except Freelancer.DoesNotExist:
            return Response(
                {'error': 'Freelancer profile not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get tasks that are available and user hasn't bid on yet
        queryset = self.get_queryset().filter(status='available').exclude(
            bids__freelancer=freelancer  # Use freelancer instance if Bid model references Freelancer
            # OR use bids__freelancer__user=request.user if Bid model references User
        )
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = ServiceListSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        
        serializer = ServiceListSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def my_bids(self, request, *args, **kwargs):
        """
        Get all bids made by the authenticated freelancer
        """
        # Check if user is authenticated and is a freelancer
        if not request.user.is_authenticated:
            return Response(
                {"error": "Authentication required"}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        if not request.user.is_freelancer:
            return Response(
                {"error": "Only freelancers can view their bids"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            # Get the freelancer profile
            freelancer = request.user.freelancer_profile
            
            # Query the Bid model directly, not BaseService
            # Assuming your Bid model has a freelancer field pointing to Freelancer
            queryset = Bid.objects.filter(freelancer=freelancer).select_related(
                'service', 'freelancer__user'
            ).order_by('-created_at')
            
            # Apply pagination
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = BidSerializer(page, many=True, context={'request': request})
                return self.get_paginated_response(serializer.data)
            
            serializer = BidSerializer(queryset, many=True, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Freelancer.DoesNotExist:
            return Response(
                {"error": "Freelancer profile not found. Please contact support."}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": f"An error occurred: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def add_admin_feedback(self, request, pk=None):
        """Add admin feedback for completed task"""
        order = self.get_object()
        if order.status != 'completed':
            return Response({'error': 'Can only add feedback to completed tasks'}, 
                        status=status.HTTP_400_BAD_REQUEST)
        
        serializer = AdminFeedbackSerializer(data=request.data)
        if serializer.is_valid():
            # Create feedback record
            feedback = AdminFeedback.objects.create(
                order=order,
                rating=serializer.validated_data['rating'],
                comment=serializer.validated_data['comment'],
                provided_by=request.user
            )
            return Response({'message': 'Feedback added successfully'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
# Simplified specialized service ViewSets
class BaseReadOnlyServiceViewSet(BasePermissionMixin, viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.request.user.is_staff:
            try:
                freelancer = self.request.user.freelancer_profile
                return queryset.filter(
                    Q(user=self.request.user) | Q(assigned_to=freelancer)
                ).distinct()
            except:
                return queryset.filter(user=self.request.user)
        return queryset

class SoftwareServiceViewSet(BaseReadOnlyServiceViewSet):
    queryset = SoftwareService.objects.select_related('user', 'assigned_to').prefetch_related('files')
    serializer_class = SoftwareServiceSerializer
    search_fields = ['title', 'description', 'frontend_languages', 'backend_languages']

class ResearchServiceViewSet(BaseReadOnlyServiceViewSet):
    queryset = ResearchService.objects.select_related('user', 'assigned_to').prefetch_related('files')
    serializer_class = ResearchServiceSerializer
    search_fields = ['title', 'description', 'academic_writing_type', 'citation_style']

class CustomServiceViewSet(BaseReadOnlyServiceViewSet):
    queryset = CustomService.objects.select_related('user', 'assigned_to').prefetch_related('files')
    serializer_class = CustomServiceSerializer
    search_fields = ['title', 'description', 'service_id']


class ServiceFileViewSet(viewsets.ModelViewSet):
    queryset = ServiceFile.objects.select_related('service')
    serializer_class = ServiceFileSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['service__service_type']

    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.request.user.is_staff:
            return queryset.filter(service__user=self.request.user)
        return queryset

class BidViewSet(viewsets.ModelViewSet):
    queryset = Bid.objects.select_related('order', 'freelancer', 'freelancer__user', 'order__user')
    serializer_class = BidSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = BidFilter
    search_fields = ['order__title', 'order__description', 'proposal']
    ordering_fields = ['created_at', 'bid_amount', 'estimated_hours']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'create':
            return BidCreateSerializer
        return BidSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        
        if self.request.user.is_staff or self.request.user.is_admin:
            # Admin can see all bids with full information
            return queryset.select_related(
                'order__user', 
                'freelancer__user'
            ).prefetch_related(
                'order__files',
                'order__comments'
            )
        
        if self.request.user.is_freelancer:
            try:
                # Get the freelancer instance for this user
                freelancer = Freelancer.objects.get(user=self.request.user)
                # Freelancer can see their own bids with client info
                return queryset.filter(freelancer=freelancer).select_related(
                    'order__user',  # Client info
                    'order'  # Order details
                )
            except Freelancer.DoesNotExist:
                return queryset.none()
        
        # Clients can see bids on their own orders with freelancer info
        return queryset.filter(order__user=self.request.user).select_related(
            'freelancer__user',  # Freelancer info
            'freelancer',        # Freelancer profile
            'order'              # Order details
        )

    def perform_create(self, serializer):
        if not self.request.user.is_freelancer:
            raise ValidationError("You must be a freelancer to place bids")
        
        try:
            freelancer = Freelancer.objects.get(user=self.request.user)
            serializer.save(freelancer=freelancer)
        except Freelancer.DoesNotExist:
            raise ValidationError("Freelancer profile not found")

    @action(detail=True, methods=['post'])
    def withdraw(self, request, pk=None):
        bid = self.get_object()
        try:
            freelancer = Freelancer.objects.get(user=request.user)
            if bid.freelancer != freelancer:
                return Response(
                    {'error': 'You can only withdraw your own bids'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
        except Freelancer.DoesNotExist:
            return Response(
                {'error': 'Freelancer profile not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        if bid.status != 'pending':
            return Response(
                {'error': f'Cannot withdraw {bid.status} bid'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        bid.status = 'withdrawn'
        bid.withdrawn_at = timezone.now()
        bid.save()
        
        return Response({
            'message': 'Bid withdrawn successfully',
            'bid': BidSerializer(bid, context={'request': request}).data
        })

    @action(detail=True, methods=['patch'])
    def update_bid(self, request, pk=None):
        bid = self.get_object()
        try:
            freelancer = Freelancer.objects.get(user=request.user)
            if bid.freelancer != freelancer:
                return Response(
                    {'error': 'You can only update your own bids'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
        except Freelancer.DoesNotExist:
            return Response(
                {'error': 'Freelancer profile not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        if bid.status != 'pending':
            return Response(
                {'error': f'Cannot update {bid.status} bid'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        allowed_fields = ['bid_amount', 'estimated_hours', 'proposal']
        update_data = {k: v for k, v in request.data.items() if k in allowed_fields}
        
        serializer = BidSerializer(bid, data=update_data, partial=True, context={'request': request})
        
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Bid updated successfully',
                'bid': serializer.data
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def my_bids(self, request):
        """Get all bids made by the authenticated freelancer with client and order info"""
        if not request.user.is_freelancer:
            return Response(
                {"error": "Only freelancers can view their bids"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            freelancer = request.user.freelancer_profile
            queryset = self.get_queryset().filter(freelancer=freelancer)
            
            # Apply additional filters if provided
            status_filter = request.query_params.get('status')
            if status_filter:
                queryset = queryset.filter(status=status_filter)
            
            search = request.query_params.get('search')
            if search:
                queryset = queryset.filter(
                    Q(order__title__icontains=search) |
                    Q(order__description__icontains=search) |
                    Q(proposal__icontains=search)
                )
            
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = BidSerializer(page, many=True, context={'request': request})
                return self.get_paginated_response(serializer.data)
            
            serializer = BidSerializer(queryset, many=True, context={'request': request})
            return Response(serializer.data)
            
        except Freelancer.DoesNotExist:
            return Response(
                {"error": "Freelancer profile not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )


    @action(detail=False, methods=['get'])
    def statistics(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        
        stats = {
            'total_bids': queryset.count(),
            'pending_bids': queryset.filter(status='pending').count(),
            'approved_bids': queryset.filter(status='approved').count(),
            'rejected_bids': queryset.filter(status='rejected').count(),
            'withdrawn_bids': queryset.filter(status='withdrawn').count(),
            'under_review_bids': queryset.filter(status='under_review').count(),
            'success_rate': queryset.filter(status='approved').count() / max(1, queryset.exclude(status='pending').count()),
            'average_bid_amount': queryset.aggregate(avg=Avg('bid_amount'))['avg'] or 0,
            'total_bid_value': queryset.aggregate(total=Sum('bid_amount'))['total'] or 0
        }
        return Response(stats)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def reject_bid(self, request, pk=None):
        """Reject a specific bid"""
        bid = self.get_object()
        
        if bid.status != 'pending':
            return Response(
                {'error': f'Cannot reject {bid.status} bid. Only pending bids can be rejected.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        note = request.data.get('note', '')
        
        # Update bid status
        bid.status = 'rejected'
        bid.rejected_by = request.user
        bid.rejected_at = timezone.now()
        bid.rejection_note = note
        bid.save()
        
        # Create order status history entry
        OrderStatusHistory.objects.create(
            order=bid.order,
            previous_status=bid.order.status,
            new_status=bid.order.status,  # Order status doesn't change
            changed_by=request.user,
            notes=f"Bid from {bid.freelancer.name} rejected. Amount: ${bid.bid_amount}. Note: {note}".strip()
        )
        
        return Response({
            'message': f'Bid from {bid.freelancer.name} rejected successfully',
            'bid': BidSerializer(bid, context={'request': request}).data
        })

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def mark_under_review(self, request, pk=None):
        """Mark a bid as under review"""
        bid = self.get_object()
        
        if bid.status != 'pending':
            return Response(
                {'error': f'Cannot mark {bid.status} bid under review. Only pending bids can be marked under review.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        note = request.data.get('note', '')
        
        # Update bid status
        bid.status = 'under_review'
        bid.reviewed_by = request.user
        bid.reviewed_at = timezone.now()
        bid.review_note = note
        bid.save()
        
        # Create order status history entry
        OrderStatusHistory.objects.create(
            order=bid.order,
            previous_status=bid.order.status,
            new_status=bid.order.status,  # Order status doesn't change
            changed_by=request.user,
            notes=f"Bid from {bid.freelancer.name} marked under review. Amount: ${bid.bid_amount}. Note: {note}".strip()
        )
        
        return Response({
            'message': f'Bid from {bid.freelancer.name} marked under review',
            'bid': BidSerializer(bid, context={'request': request}).data
        })

    @action(detail=True, methods=['post'])
    def request_revision(self, request, pk=None):
        """Request revision for a bid (available to both admin and bid owner)"""
        bid = self.get_object()
        
        # Check permissions - admin or bid owner
        is_admin = request.user.is_staff
        is_bid_owner = False
        
        try:
            freelancer = Freelancer.objects.get(user=request.user)
            is_bid_owner = bid.freelancer == freelancer
        except Freelancer.DoesNotExist:
            pass
        
        if not (is_admin or is_bid_owner):
            return Response(
                {'error': 'You can only request revision for your own bids or as an admin'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        if bid.status not in ['pending', 'under_review']:
            return Response(
                {'error': f'Cannot request revision for {bid.status} bid. Only pending or under review bids can be revised.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        note = request.data.get('note', '')
        if not note.strip():
            return Response(
                {'error': 'Revision note is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update bid status
        previous_status = bid.status
        bid.status = 'revision_requested'
        bid.revision_requested_by = request.user
        bid.revision_requested_at = timezone.now()
        bid.revision_note = note
        bid.save()
        
        # Create order status history entry
        requester = "Admin" if is_admin else bid.freelancer.name
        OrderStatusHistory.objects.create(
            order=bid.order,
            previous_status=bid.order.status,
            new_status=bid.order.status,  # Order status doesn't change
            changed_by=request.user,
            notes=f"Revision requested for bid from {bid.freelancer.name} by {requester}. Amount: ${bid.bid_amount}. Note: {note}"
        )
        
        return Response({
            'message': f'Revision requested for bid from {bid.freelancer.name}',
            'bid': BidSerializer(bid, context={'request': request}).data
        })

    @action(detail=True, methods=['post'])
    def revise_bid(self, request, pk=None):
        """Submit a revised bid (freelancer only)"""
        bid = self.get_object()
        
        try:
            freelancer = Freelancer.objects.get(user=request.user)
            if bid.freelancer != freelancer:
                return Response(
                    {'error': 'You can only revise your own bids'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
        except Freelancer.DoesNotExist:
            return Response(
                {'error': 'Freelancer profile not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        if bid.status != 'revision_requested':
            return Response(
                {'error': f'Cannot revise {bid.status} bid. Only bids with requested revisions can be revised.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate revision data
        allowed_fields = ['bid_amount', 'estimated_hours', 'proposal']
        update_data = {k: v for k, v in request.data.items() if k in allowed_fields}
        
        if not update_data:
            return Response(
                {'error': 'At least one field (bid_amount, estimated_hours, proposal) must be updated'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update bid with revised data
        for field, value in update_data.items():
            setattr(bid, field, value)
        
        bid.status = 'pending'  # Back to pending for review
        bid.revised_at = timezone.now()
        bid.revision_count = (bid.revision_count or 0) + 1
        bid.save()
        
        # Create order status history entry
        OrderStatusHistory.objects.create(
            order=bid.order,
            previous_status=bid.order.status,
            new_status=bid.order.status,  # Order status doesn't change
            changed_by=request.user,
            notes=f"Bid revised by {bid.freelancer.name}. New amount: ${bid.bid_amount}. Revision #{bid.revision_count}"
        )
        
        return Response({
            'message': 'Bid revised successfully and submitted for review',
            'bid': BidSerializer(bid, context={'request': request}).data
        })
    
@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_dashboard(request):
    """
    Comprehensive admin dashboard endpoint that provides all necessary data
    for the admin dashboard in a single request.
    """
    # Calculate time ranges for analytics
    now = timezone.now()
    thirty_days_ago = now - timedelta(days=30)
    sixty_days_ago = now - timedelta(days=60)
    
    # Get base querysets
    tasks = BaseService.objects.all()
    freelancers = Freelancer.objects.all()
    clients = User.objects.filter(user_type='client')
    
    # Calculate completed and pending services
    completed_services = tasks.filter(status='completed').count()
    pending_services = tasks.filter(status='pending').count()
    active_services = tasks.filter(status__in=['in_progress', 'assigned', 'start_working']).count()
    
    # Calculate revenue metrics
    total_revenue = tasks.filter(
        status='completed', 
        payment_status='paid'
    ).aggregate(total=Sum('cost'))['total'] or Decimal('0.00')
    
    monthly_revenue = tasks.filter(
        status='completed',
        payment_status='paid',
        completed_at__gte=thirty_days_ago
    ).aggregate(total=Sum('cost'))['total'] or Decimal('0.00')
    
    # Calculate average service value
    avg_service_value = tasks.filter(
        status='completed'
    ).aggregate(avg=Avg('cost'))['avg'] or Decimal('0.00')
    
    # Calculate revenue growth (comparing last 30 days to previous 30 days)
    previous_month_revenue = tasks.filter(
        status='completed',
        payment_status='paid',
        completed_at__gte=sixty_days_ago,
        completed_at__lt=thirty_days_ago
    ).aggregate(total=Sum('cost'))['total'] or Decimal('0.00')
    
    revenue_growth = 0
    if previous_month_revenue > 0:
        revenue_growth = ((monthly_revenue - previous_month_revenue) / previous_month_revenue) * 100
    
    # Calculate completion rate
    total_assigned = tasks.filter(status__in=['completed', 'in_progress', 'cancelled']).count()
    completion_rate = (completed_services / total_assigned * 100) if total_assigned > 0 else 0
    
    # Calculate average rating
    avg_rating = freelancers.aggregate(avg=Avg('average_rating'))['avg'] or 0
    
    # Total bids
    total_bids = Bid.objects.count()
    
    # Dashboard statistics matching frontend expectations
    stats = {
        # Overview stats
        'total_services': tasks.count(),
        'active_services': active_services,
        'completed_services': completed_services,
        'pending_services': pending_services,
        
        # Financial stats
        'total_revenue': float(total_revenue),
        'monthly_revenue': float(monthly_revenue),
        'average_service_value': float(avg_service_value),
        'revenue_growth': float(revenue_growth),
        
        # User stats
        'total_freelancers': freelancers.count(),
        'active_freelancers': freelancers.filter(is_available=True).count(),
        'total_clients': clients.count(),
        'new_clients_this_month': clients.filter(
            created_at__gte=thirty_days_ago
        ).count(),
        
        # Performance stats
        'completion_rate': completion_rate,
        'average_rating': float(avg_rating),
        'total_bids': total_bids,
        
        # Charts data
        'revenue_chart': get_revenue_chart_data(now),
        'service_status_chart': get_service_status_chart(),
        'category_distribution': get_category_distribution(),
        
        # Recent activities
        'recent_services': get_recent_services_fixed(),
        'recent_activities': get_recent_activities_fixed(),
    }
    
    return Response(stats)

def get_recent_services_fixed():
    """
    Get recent services with proper select_related fields
    """
    return BaseService.objects.select_related(
        'user',  # Instead of 'client'
        'assigned_to',  # Instead of 'assigned_freelancer'
        'review'
    ).order_by('-created_at')[:10].values(
        'id',
        'title', 
        'status',
        'cost',
        'created_at',
        'user__first_name',  # Client name
        'user__last_name',
        'assigned_to__user__first_name',  # Freelancer name
        'assigned_to__user__last_name',
        'review__rating'
    )

def get_recent_activities_fixed():
    """
    Get recent activities with proper select_related fields
    """
    return BaseService.objects.select_related(
        'user',
        'assigned_to'
    ).order_by('-updated_at')[:15].values(
        'id',
        'title',
        'status', 
        'updated_at',
        'user__first_name',
        'user__last_name',
        'assigned_to__user__first_name',
        'assigned_to__user__last_name'
    )

def get_revenue_chart_data(now):
    """
    Generate revenue chart data for the last 12 months
    """
    chart_data = []
    for i in range(12):
        month_start = now.replace(day=1) - timedelta(days=30*i)
        month_end = month_start + timedelta(days=31)
        
        monthly_revenue = BaseService.objects.filter(
            status='completed',
            payment_status='paid',
            completed_at__gte=month_start,
            completed_at__lt=month_end
        ).aggregate(total=Sum('cost'))['total'] or 0
        
        chart_data.append({
            'month': month_start.strftime('%b %Y'),
            'revenue': float(monthly_revenue)
        })
    
    return list(reversed(chart_data))

def get_service_status_chart():
    """
    Get service status distribution for pie chart
    """
    status_counts = BaseService.objects.values('status').annotate(
        count=Count('id')
    ).order_by('status')
    
    return [
        {
            'status': item['status'].title(),
            'count': item['count']
        }
        for item in status_counts
    ]

def get_category_distribution():
    """
    Get service category distribution
    """
    # Since you're using polymorphic models, get counts by service type
    software_count = BaseService.objects.filter(
        polymorphic_ctype__model='softwareservice'
    ).count()
    
    research_count = BaseService.objects.filter(
        polymorphic_ctype__model='researchservice'
    ).count()
    
    custom_count = BaseService.objects.filter(
        polymorphic_ctype__model='customservice'
    ).count()
    
    return [
        {'category': 'Software Services', 'count': software_count},
        {'category': 'Research Services', 'count': research_count},
        {'category': 'Custom Services', 'count': custom_count},
    ]


@api_view(['GET'])
@permission_classes([IsAdminUser])
def freelancer_stats(request):
    """Additional freelancer statistics"""
    freelancers = Freelancer.objects.all()
    
    stats = {
        'total_freelancers': freelancers.count(),
        'available_freelancers': freelancers.filter(is_available=True).count(),
        'busy_freelancers': freelancers.filter(is_available=False).count(),
        'new_freelancers': freelancers.filter(
            created_at__gte=timezone.now() - timedelta(days=30)
        ).count(),
        'experience_distribution': freelancers.values('experience_level').annotate(
            count=Count('id')
        ).order_by('experience_level'),
        'average_rating': freelancers.aggregate(
            avg=Avg('average_rating')
        )['avg'] or 0,
        'top_skills': get_top_skills(freelancers),
    }
    
    return Response(stats)



def get_recent_services():
    """Get recent services data"""
    recent_services = BaseService.objects.select_related(
        'client', 'assigned_freelancer'
    ).order_by('-created_at')[:10]
    
    services_data = []
    for service in recent_services:
        services_data.append({
            'id': str(service.id),
            'title': service.title,
            'status': service.status,
            'budget': float(service.cost),
            'deadline': service.deadline.isoformat() if service.deadline else None,
            'createdAt': service.created_at.isoformat(),
            'clientId': str(service.client.id) if service.client else None,
            'client_name': service.client.get_full_name() if service.client else 'Unknown',
            'freelancer_name': service.assigned_freelancer.user.get_full_name() if service.assigned_freelancer else None,
            'service_type': getattr(service, 'service_type', 'General'),
        })
    
    return services_data


def get_recent_activities():
    """Get recent platform activities"""
    activities = []
    
    # Get recent service status changes
    recent_services = BaseService.objects.order_by('-updated_at')[:5]
    for service in recent_services:
        activities.append({
            'id': f"service_{service.id}",
            'action': f"Service {service.status.replace('_', ' ').title()}",
            'description': f"Service '{service.title}' status changed to {service.status}",
            'timestamp': service.updated_at.isoformat(),
            'user_type': 'client',
            'user_name': service.client.get_full_name() if service.client else 'Unknown'
        })
    
    # Sort by timestamp and return recent ones
    activities.sort(key=lambda x: x['timestamp'], reverse=True)
    return activities[:10]


def get_top_skills(freelancers):
    """Extract top skills from freelancer profiles"""
    skills = {}
    for freelancer in freelancers.only('skills'):
        if hasattr(freelancer, 'skills') and freelancer.skills:
            for skill in freelancer.skills:
                if isinstance(skill, dict):
                    skill_name = skill.get('name', '')
                    if skill_name:
                        skills[skill_name] = skills.get(skill_name, 0) + 1
                else:
                    skills[str(skill)] = skills.get(str(skill), 0) + 1
    
    return sorted(
        [{'skill': k, 'count': v} for k, v in skills.items()],
        key=lambda x: x['count'],
        reverse=True
    )[:10]