from django.shortcuts import get_object_or_404
from django.http import JsonResponse, FileResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from service.models import Service
from .utils import generate_financial_pdf, generate_contract_pdf 
from django.db.models import Sum

class OrderAnalyticsView(APIView):
    permission_classes = [IsAuthenticated]  # Ensures only authenticated users can access

    def get(self, request, service_id):
        # Ensure the service belongs to the logged-in user
        service = get_object_or_404(Service, service_id=service_id, user=request.user)

        # If user is authenticated and service belongs to them, return analytics data
        data = {
            'service_id': service.service_id,
            'title': service.title,
            'cost': str(service.cost),
            'payment_status': service.payment_status,
            'order_status': service.order_status,
        }
        return JsonResponse(data)

    def get_pdf(self, request, service_id, type):
        # Ensure the service belongs to the logged-in user
        service = get_object_or_404(Service, service_id=service_id, user=request.user)

        # Generate the appropriate PDF based on type
        if type == 'financial':
            pdf = generate_financial_pdf(service)  # Assume a utility to generate the financial PDF
        elif type == 'contract':
            pdf = generate_contract_pdf(service)  # Assume a utility to generate the contract PDF
        else:
            return JsonResponse({'error': 'Invalid PDF type'}, status=400)

        # Return PDF as FileResponse for download
        response = FileResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename={service.service_id}_{type}.pdf'
        return response

class GeneralAnalyticsView(APIView):
    permission_classes = [IsAuthenticated]  # Ensures only authenticated users can access

    def get(self, request):
        # Calculate general analytics for the authenticated user
        total_orders = Service.objects.filter(user=request.user).count()
        total_revenue = Service.objects.filter(user=request.user).aggregate(Sum('cost'))['cost__sum'] or 0
        completed_orders = Service.objects.filter(user=request.user, order_status='completed').count()
        pending_orders = Service.objects.filter(user=request.user, order_status='processing').count()
        failed_orders = Service.objects.filter(user=request.user, payment_status='failed').count()

        data = {
            'total_orders': total_orders,
            'total_revenue': f"${total_revenue:,.2f}",
            'completed_orders': completed_orders,
            'pending_orders': pending_orders,
            'failed_orders': failed_orders,
        }
        return JsonResponse(data)
