from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

def generate_financial_pdf(service):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    
    c.drawString(100, 750, f"Order ID: {service.service_id}")
    c.drawString(100, 730, f"Service: {service.title}")
    c.drawString(100, 710, f"Cost: ${service.cost}")
    c.drawString(100, 690, f"Payment Status: {service.payment_status}")
    c.drawString(100, 670, f"Order Status: {service.order_status}")
    
    c.showPage()
    c.save()

    buffer.seek(0)
    return buffer

def generate_contract_pdf(service):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    
    c.drawString(100, 750, f"Contract for Service: {service.title}")
    c.drawString(100, 730, f"Order ID: {service.service_id}")
    c.drawString(100, 710, f"Cost: ${service.cost}")
    
    c.showPage()
    c.save()

    buffer.seek(0)
    return buffer
