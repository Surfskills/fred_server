import logging
from django.conf import settings
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.http import HttpResponse, FileResponse
from rest_framework import serializers
import os
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from urllib.parse import quote as urlquote
from .models import Document, DocumentRequirement
from .serializers import DocumentSerializer, DocumentRequirementSerializer
from .permissions import IsOwnerOrStaff, CanVerifyDocument

# Configure logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class DocumentViewSet(viewsets.ModelViewSet):
    serializer_class = DocumentSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrStaff]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description', 'file_name']
    ordering_fields = ['name', 'created_at', 'updated_at', 'status']
    ordering = ['-updated_at']
    
    def get_queryset(self):
        user = self.request.user
        queryset = Document.objects.all()
        
        # Apply user_id filter if provided
        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        # Permission checks
        if user.is_staff and user.has_perm('documents.view_all_documents'):
            return queryset
        return queryset.filter(user=user)
    
    def perform_create(self, serializer):
        user = self.request.user
        logger.debug(f"Creating document for user: {user}")
        file_uploaded = self.request.FILES.get('file')
        print(f"File uploaded: {file_uploaded}")
        status_value = 'pending' if file_uploaded else 'required'
        logger.debug(f"Assigned status: {status_value}")
        serializer.save(user=user, status=status_value)
    
    def perform_update(self, serializer):
        instance = self.get_object()
        logger.debug(f"Updating document: {instance.pk}")
        file_updated = 'file' in self.request.FILES
        print(f"File being updated: {file_updated}")
        if file_updated:
            logger.debug("New file uploaded. Setting status to 'pending'.")
            serializer.save(status='pending')
        else:
            logger.debug("No new file uploaded. Keeping current status.")
            serializer.save()
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated, CanVerifyDocument])
    def verify(self, request, pk=None):
        logger.debug(f"Verifying document with pk={pk} by user={request.user}")
        document = self.get_object()
        status_value = request.data.get('status', 'verified')
        notes = request.data.get('verification_notes', '')
        logger.debug(f"Received verification status: {status_value}, notes: {notes}")

        if status_value not in ['verified', 'pending', 'missing', 'required']:
            logger.warning(f"Invalid status value received: {status_value}")
            return Response(
                {'detail': 'Invalid status value.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        document.status = status_value
        if status_value == 'verified':
            document.verification_date = timezone.now()
            document.verified_by = request.user
            logger.debug("Document marked as verified.")
        document.verification_notes = notes
        document.save()
        serializer = self.get_serializer(document)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def filter_by_status(self, request):
        status_value = request.query_params.get('status', '')
        logger.debug(f"Filtering documents by status: {status_value}")
        queryset = self.get_queryset().filter(status=status_value) if status_value else self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def validate_file(self, value):
        """Validate uploaded file size and type."""
        if not value:
            return value

        document_type = self.initial_data.get('document_type', '')
        name = self.initial_data.get('name', '')
        logger.debug(f"Validating file upload: name={name}, document_type={document_type}, size={value.size}")

        requirement = None
        try:
            requirement = DocumentRequirement.objects.filter(
                name__iexact=name,
                active=True
            ).first() or DocumentRequirement.objects.filter(
                document_type=document_type,
                active=True
            ).first()
        except Exception as e:
            logger.warning(f"Error while fetching DocumentRequirement: {e}")

        # Use specific requirement size limit
        if requirement and requirement.max_file_size:
            if value.size > requirement.max_file_size:
                max_size_mb = requirement.max_file_size / (1024 * 1024)
                logger.warning(f"File size {value.size} exceeds max {requirement.max_file_size}")
                raise serializers.ValidationError(
                    f"File is too large. Maximum size is {max_size_mb:.1f} MB."
                )
        else:
            # Fallback to global or default size limit (e.g., 5MB)
            fallback_limit = getattr(settings, 'MAX_UPLOAD_SIZE', 5 * 1024 * 1024)
            if value.size > fallback_limit:
                max_size_mb = fallback_limit / (1024 * 1024)
                logger.warning(f"File size {value.size} exceeds fallback limit of {fallback_limit}")
                raise serializers.ValidationError(
                    f"File is too large. Maximum size is {max_size_mb:.1f} MB."
                )

        # Validate extension if applicable
        if requirement and requirement.allowed_extensions:
            allowed_exts = [ext.strip().lower() for ext in requirement.allowed_extensions.split(',') if ext.strip()]
            file_ext = f".{value.name.split('.')[-1].lower()}" if '.' in value.name else ''
            if allowed_exts and file_ext and file_ext not in allowed_exts:
                logger.warning(f"Invalid file extension: {file_ext}. Allowed: {allowed_exts}")
                raise serializers.ValidationError(
                    f"Invalid file extension. Allowed extensions are: {requirement.allowed_extensions}"
                )

        return value
    @action(detail=True, methods=['get'])
    def view(self, request, pk=None):
        """
        Handle document viewing with token authentication
        """
        # Check for token in both header and query params
        token = request.META.get('HTTP_AUTHORIZATION', '').split('Bearer ')[-1] or request.GET.get('token')
        
        if not token:
            return Response({'error': 'Authentication required'}, status=401)
        
        # Verify token (pseudo-code - implement your actual token verification)
        if not self._verify_token(token):
            return Response({'error': 'Invalid token'}, status=403)

        document = self.get_object()
        
        if not document.file:
            return Response({'error': 'Document file not found'}, status=404)

        try:
            file_path = document.file.path
            if not os.path.exists(file_path):
                return Response({'error': 'File not found on server'}, status=404)

            # Determine content type
            ext = os.path.splitext(file_path)[1].lower()
            content_type = {
                '.pdf': 'application/pdf',
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
            }.get(ext, 'application/octet-stream')

            response = FileResponse(open(file_path, 'rb'), content_type=content_type)
            response['Content-Disposition'] = f'inline; filename="{unquote(document.file.name)}"'
            return response

        except Exception as e:
            return Response({'error': str(e)}, status=500)

    def _verify_token(self, token):
        """Implement your actual token verification logic"""
        from rest_framework.authtoken.models import Token
        return Token.objects.filter(key=token).exists()


    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """
        Download a document as attachment
        """
        document = self.get_object()
        logger.debug(f"Attempting to download document ID {document.id}")

        if not document.file:
            logger.warning("Document has no file attached")
            return Response(
                {'error': 'No file available for this document'},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            file_path = document.file.path
            if not os.path.exists(file_path):
                logger.error(f"File not found at path: {file_path}")
                return Response(
                    {'error': 'Document file not found on server'},
                    status=status.HTTP_404_NOT_FOUND
                )

            response = FileResponse(open(file_path, 'rb'))
            response['Content-Type'] = 'application/octet-stream'
            response['Content-Disposition'] = f'attachment; filename="{quote(document.file.name)}"'
            return response

        except Exception as e:
            logger.error(f"Error downloading document: {str(e)}")
            return Response(
                {'error': 'Failed to download document'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _get_content_type(self, filename):
        """Determine content type based on file extension"""
        ext = os.path.splitext(filename)[1].lower()
        return {
            '.pdf': 'application/pdf',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.txt': 'text/plain',
            '.html': 'text/html',
        }.get(ext, 'application/octet-stream')

class DocumentRequirementViewSet(viewsets.ModelViewSet):
    queryset = DocumentRequirement.objects.filter(active=True)
    serializer_class = DocumentRequirementSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'is_required']
    ordering = ['name']
    
    def get_permissions(self):
        logger.debug(f"Checking permissions for action: {self.action}")
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            logger.debug("Admin permissions required.")
            return [permissions.IsAdminUser()]
        return super().get_permissions()


@login_required
def document_upload_view(request):
    logger.debug(f"Handling document upload. Method: {request.method}")
    if request.method != 'POST':
        logger.warning("Invalid method for document upload.")
        return HttpResponse(status=405)
    
    viewset = DocumentViewSet.as_view({'post': 'create'})
    return viewset(request)


@login_required
def document_view(request, pk):
    logger.debug(f"Attempting to view document with pk={pk}")
    document = get_object_or_404(Document, pk=pk)
    
    if document.user != request.user and not (
        request.user.is_staff and 
        request.user.has_perm('documents.view_all_documents')
    ):
        logger.warning("Permission denied when viewing document.")
        raise PermissionDenied("You don't have permission to view this document.")
    
    if not document.file:
        logger.warning("Document has no file.")
        return HttpResponse("No file available for this document.", status=404)
    
    displayable_types = [
        'application/pdf',
        'image/jpeg',
        'image/png',
        'image/gif',
        'text/plain',
        'text/html'
    ]
    
    disposition = 'inline' if document.content_type in displayable_types else 'attachment'
    logger.debug(f"Content-Disposition set to: {disposition}")

    response = FileResponse(document.file)
    response['Content-Type'] = document.content_type or 'application/octet-stream'
    response['Content-Disposition'] = f'{disposition}; filename="{urlquote(document.file_name or document.file.name)}"'
    
    return response


@login_required
def document_download_view(request, pk):
    logger.debug(f"Attempting to download document with pk={pk}")
    document = get_object_or_404(Document, pk=pk)
    
    if document.user != request.user and not (
        request.user.is_staff and 
        request.user.has_perm('documents.view_all_documents')
    ):
        logger.warning("Permission denied when downloading document.")
        raise PermissionDenied("You don't have permission to download this document.")
    
    if not document.file:
        logger.warning("Document has no file.")
        return HttpResponse("No file available for this document.", status=404)
    
    response = FileResponse(document.file)
    response['Content-Type'] = document.content_type or 'application/octet-stream'
    response['Content-Disposition'] = f'attachment; filename="{urlquote(document.file_name or document.file.name)}"'
    
    return response
