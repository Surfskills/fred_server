from django.shortcuts import get_object_or_404
from django.http import JsonResponse, FileResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from service.models import Service
from .utils import generate_financial_pdf, generate_contract_pdf
from django.db.models import Sum

class OrderAnalyticsView(APIView):
    permission_classes = [IsAuthenticated]  # Ensures only authenticated users can access

    def get(self, request, id, type):
        """
        Handles the request to generate either a financial or contract PDF for the specified service order.

        :param request: The HTTP request object
        :param id: The ID of the service/order
        :param type: The type of PDF to generate ('financial' or 'contract')
        """
        # Ensure the service belongs to the logged-in user by matching the id and user
        service = get_object_or_404(Service, id=id, user=request.user)  

        # Check the 'type' argument and generate the correct PDF
        if type == 'financial':
            pdf = generate_financial_pdf(service)  # Generate the financial PDF
        elif type == 'contract':
            pdf = generate_contract_pdf(service)  # Generate the contract PDF
        else:
            return JsonResponse({'error': 'Invalid PDF type'}, status=400)

        # Return the PDF as FileResponse for download
        response = FileResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename={service.id}_{type}.pdf'  # Use `service.id`
        return response

class GeneralAnalyticsView(APIView):
    permission_classes = [IsAuthenticated]  # Ensures only authenticated users can access

    def get(self, request):
        """
        Retrieves general analytics for the authenticated user, including total orders, total revenue, 
        and the count of completed, pending, and failed orders.
        """
        # Calculate general analytics for the authenticated user based on `id`
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
