# from rest_framework import viewsets, status
# from rest_framework.response import Response
# from rest_framework.permissions import IsAuthenticated
# from rest_framework.decorators import action
# from django.db.models import Q, Value, CharField
# from django.db.models.functions import Cast
# from rest_framework.exceptions import PermissionDenied
# from itertools import chain
# from .models import SoftwareRequest, ResearchRequest
# from .serializers import (
#     SoftwareRequestSerializer,
#     ResearchRequestSerializer,
# )
# import uuid

# class RequestViewSet(viewsets.ViewSet):
#     permission_classes = [IsAuthenticated]
#     http_method_names = ['get', 'post', 'put', 'patch', 'delete']

#     def get_queryset(self, request_type=None):
#         user = self.request.user
        
#         if request_type == 'software':
#             return SoftwareRequest.objects.filter(user=user)
#         elif request_type == 'research':
#             return ResearchRequest.objects.filter(user=user)
        
#         # Ensure user filtering for both querysets
#         software_requests = SoftwareRequest.objects.filter(user=user).annotate(
#             model_type=Value('software', output_field=CharField()),
#             # Add NULL values for research-specific fields
#             academic_writing_type=Value(None, output_field=CharField(null=True)),
#             writing_technique=Value(None, output_field=CharField(null=True)),
#             academic_writing_style=Value(None, output_field=CharField(null=True)),
#             critical_writing_type=Value(None, output_field=CharField(null=True)),
#             critical_thinking_skill=Value(None, output_field=CharField(null=True)),
#             critical_writing_structure=Value(None, output_field=CharField(null=True)),
#             discussion_type=Value(None, output_field=CharField(null=True)),
#             discussion_component=Value(None, output_field=CharField(null=True)),
#             citation_style=Value(None, output_field=CharField(null=True)),
#             number_of_pages=Value(None, output_field=CharField(null=True)),
#             number_of_references=Value(None, output_field=CharField(null=True)),
#             study_level=Value(None, output_field=CharField(null=True))
#         ).values(
#             'id', 'title', 'project_description', 'request_type',
#             'created_at', 'updated_at', 'user_id', 'model_type',
#             'status', 'payment_status', 'order_status', 'cost',
#             'budget_range', 'timeline', 'frontend_languages',
#             'frontend_frameworks', 'backend_languages', 'backend_frameworks',
#             'ai_languages', 'ai_frameworks',
#             'academic_writing_type', 'writing_technique',
#             'academic_writing_style', 'critical_writing_type',
#             'critical_thinking_skill', 'critical_writing_structure',
#             'discussion_type', 'discussion_component',
#             'citation_style', 'number_of_pages', 'number_of_references',
#             'study_level'
#         )
        
#         research_requests = ResearchRequest.objects.filter(user=user).annotate(
#             model_type=Value('research', output_field=CharField()),
#             # Add NULL values for software-specific fields
#             budget_range=Value(None, output_field=CharField(null=True)),
#             timeline=Value(None, output_field=CharField(null=True)),
#             frontend_languages=Value(None, output_field=CharField(null=True)),
#             frontend_frameworks=Value(None, output_field=CharField(null=True)),
#             backend_languages=Value(None, output_field=CharField(null=True)),
#             backend_frameworks=Value(None, output_field=CharField(null=True)),
#             ai_languages=Value(None, output_field=CharField(null=True)),
#             ai_frameworks=Value(None, output_field=CharField(null=True))
#         ).values(
#             'id', 'title', 'project_description', 'request_type',
#             'created_at', 'updated_at', 'user_id', 'model_type',
#             'status', 'payment_status', 'order_status', 'cost',
#             'budget_range', 'timeline', 'frontend_languages',
#             'frontend_frameworks', 'backend_languages', 'backend_frameworks',
#             'ai_languages', 'ai_frameworks',
#             'academic_writing_type', 'writing_technique',
#             'academic_writing_style', 'critical_writing_type',
#             'critical_thinking_skill', 'critical_writing_structure',
#             'discussion_type', 'discussion_component',
#             'citation_style', 'number_of_pages', 'number_of_references',
#             'study_level'
#         )
        
#         return software_requests.union(research_requests).order_by('-created_at')

#     def get_object(self, pk):
#         """
#         Helper method to get an object, ensuring it belongs to the current user
#         """
#         user = self.request.user
        
#         try:
#             obj = SoftwareRequest.objects.get(pk=pk, user=user)
#             return obj, SoftwareRequestSerializer
#         except SoftwareRequest.DoesNotExist:
#             try:
#                 obj = ResearchRequest.objects.get(pk=pk, user=user)
#                 return obj, ResearchRequestSerializer
#             except ResearchRequest.DoesNotExist:
#                 raise PermissionDenied("Request not found or you don't have permission to access it.")

#     def list(self, request):
#         """Get all requests for the authenticated user"""
#         queryset = self.get_queryset()
#         return Response(list(queryset), status=status.HTTP_200_OK)

#     def create(self, request):
#         """Create a new request with a unique ID"""
#         request_type = request.data.get('request_type')
        
#         if not request_type:
#             return Response(
#                 {'error': 'request_type is required'},
#                 status=status.HTTP_400_BAD_REQUEST
#             )
        
#         # Add user to request data
#         data = request.data.copy()
#         data['user'] = request.user.id
        
#         # Generate a UUID to ensure uniqueness
#         unique_id = str(uuid.uuid4())
        
#         if request_type == 'software':
#             serializer = SoftwareRequestSerializer(
#                 data=data,
#                 context={'request': request}
#             )
#         elif request_type == 'research':
#             serializer = ResearchRequestSerializer(
#                 data=data,
#                 context={'request': request}
#             )
#         else:
#             return Response(
#                 {'error': f'Invalid request type: {request_type}. Allowed types: software, research'},
#                 status=status.HTTP_400_BAD_REQUEST
#             )

#         if serializer.is_valid():
#             # Since Django auto-generates IDs, we don't need to set it explicitly
#             # The unique_id could be used as a separate field if needed
#             instance = serializer.save(user=request.user)
#             return Response(serializer.data, status=status.HTTP_201_CREATED)
            
#         return Response(
#             {'error': 'Invalid data provided', 'details': serializer.errors},
#             status=status.HTTP_400_BAD_REQUEST
#         )

#     def retrieve(self, request, pk=None):
#         """Get a specific request by ID"""
#         instance, serializer_class = self.get_object(pk)
#         serializer = serializer_class(instance)
#         return Response(serializer.data)

#     def update(self, request, pk=None):
#         """Update a specific request"""
#         instance, serializer_class = self.get_object(pk)
        
#         serializer = serializer_class(
#             instance,
#             data=request.data,
#             context={'request': request},
#             partial=True
#         )

#         if serializer.is_valid():
#             serializer.save()
#             return Response(serializer.data)
            
#         return Response(
#             {'error': 'Invalid data provided', 'details': serializer.errors},
#             status=status.HTTP_400_BAD_REQUEST
#         )

#     def can_delete_request(self, instance):
#         """
#         Helper method to check if a request can be deleted based on payment status
#         """
#         if instance.payment_status == 'paid':
#             raise PermissionDenied("Cannot delete a paid order. Please contact support if you need assistance.")
#         return True
    
#     def destroy(self, request, pk=None):
#         """Delete a specific request if it hasn't been paid for"""
#         instance, _ = self.get_object(pk)
        
#         # Check if the request can be deleted
#         self.can_delete_request(instance)
        
#         instance.delete()
#         return Response(status=status.HTTP_204_NO_CONTENT)

#     @action(detail=False, methods=['get'])
#     def software(self, request):
#         """Get all software requests for the current user"""
#         queryset = self.get_queryset(request_type='software')
#         serializer = SoftwareRequestSerializer(queryset, many=True)
#         return Response(serializer.data)

#     @action(detail=False, methods=['get'])
#     def research(self, request):
#         """Get all research requests for the current user"""
#         queryset = self.get_queryset(request_type='research')
#         serializer = ResearchRequestSerializer(queryset, many=True)
#         return Response(serializer.data)