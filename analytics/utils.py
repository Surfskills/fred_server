from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.pdfgen import canvas


def generate_contract_pdf(service):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    
    # Header: Company Name and Title
    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, 770, "Remote-CTIO Service Contract")
    
    # Draw a line below the header for separation
    c.setStrokeColor(colors.grey)
    c.setLineWidth(1)
    c.line(100, 765, 500, 765)
    
    # Section Title
    c.setFont("Helvetica-Bold", 12)
    c.drawString(100, 740, f"Contract for Service: {service.title}")
    
    # Service Details Section (Body)
    c.setFont("Helvetica", 10)
    y_position = 720
    c.drawString(100, y_position, f"Order ID: {service.service_id}")
    y_position -= 20
    c.drawString(100, y_position, f"Cost: ${service.cost}")
    
    # Footer Section
    c.setFont("Helvetica", 8)
    c.drawString(100, 30, "For any queries, please contact: ojjfred@gmail.com")
    
    c.showPage()
    c.save()

    buffer.seek(0)
    return buffer

def generate_financial_pdf(service):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    
    # Header: Company Name and Title
    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, 770, "Remote-CTIO Service Financial Summary")
    
    # Draw a line below the header for separation
    c.setStrokeColor(colors.grey)
    c.setLineWidth(1)
    c.line(100, 765, 500, 765)
    
    # Section Title
    c.setFont("Helvetica-Bold", 12)
    c.drawString(100, 740, f"Order ID: {service.service_id}")
    
    # Service Details Section (Body)
    c.setFont("Helvetica", 10)
    y_position = 720
    c.drawString(100, y_position, f"Service: {service.title}")
    y_position -= 20
    c.drawString(100, y_position, f"Cost: ${service.cost}")
    y_position -= 20
    c.drawString(100, y_position, f"Payment Status: {service.payment_status}")
    y_position -= 20
    c.drawString(100, y_position, f"Order Status: {service.order_status}")
    
    # Footer Section
    c.setFont("Helvetica", 8)
    c.drawString(100, 30, "For any queries, please contact: ojjfred@gmail.com")
    
    c.showPage()
    c.save()

    buffer.seek(0)
    return buffer
