from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from service.models import Service
from django.shortcuts import get_object_or_404

def generate_contract_pdf(service_id):
    # Retrieve the service based on service_id (now using 'id' instead)
    service = get_object_or_404(Service, id=service_id)

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    
    # Header Section: Company info and title (consistent with financial PDF)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, 750, "Remote-CTIO Service Contract")
    
    company_info = [
        "Remote-CTIO",
        "Kenyalite Street, Nairobi, Kenya",
        "Email: ojjfred@gmail.com"
    ]
    c.setFont("Helvetica", 10)
    y_position = 730
    for line in company_info:
        c.drawString(100, y_position, line)
        y_position -= 15

    # Contract Title (service name)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(100, 680, f"Service Contract for: {service.title}")
    
    # Service Details Section
    c.setFont("Helvetica", 12)
    c.drawString(100, 660, f"Order ID: {service.id}")
    c.drawString(100, 640, f"Cost: ${service.cost:,.2f}")
    c.drawString(100, 620, f"Delivery Time: {service.delivery_time}")
    c.drawString(100, 600, f"Support Duration: {service.support_duration}")
    c.drawString(100, 580, f"Payment Status: {service.payment_status}")

    # Terms and Conditions
    c.setFont("Helvetica-Bold", 12)
    c.drawString(100, 540, "Terms and Conditions:")
    c.setFont("Helvetica", 10)
    terms = [
        "1. The client agrees to the service cost and payment schedule.",
        "2. Service will be rendered as per the details mentioned in the contract.",
        "3. Any amendments to the service must be mutually agreed upon by both parties.",
        "4. All payments are due within 30 days of the invoice date.",
        "5. Late payments will incur a 5% monthly interest fee."
    ]
    y_position = 520
    for term in terms:
        c.drawString(100, y_position, term)
        y_position -= 20

    # Footer
    c.setFont("Helvetica", 8)
    c.drawString(100, 100, "For any queries, please contact us at ojjfred@gmail.com")
    
    c.showPage()
    c.save()

    buffer.seek(0)
    return buffer


def generate_financial_pdf(service_id):
    # Retrieve the service based on service_id (now using 'id' instead)
    service = get_object_or_404(Service, id=service_id)

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)

    # Styles
    styles = getSampleStyleSheet()
    title_style = styles['Title']
    normal_style = styles['Normal']
    centered_style = ParagraphStyle('Centered', alignment=1, fontSize=10)
    
    # Create a list of elements to add to the PDF
    elements = []
    
    # Header Section: Company info and title (consistent with contract PDF)
    header = Paragraph("<b>Remote-CTIO Financial Statement</b>", title_style)
    company_info = Paragraph("<b>Remote-CTIO</b><br/>Kenyalite Access, Nairobi<br/>Email: ojjfred@gmail.com", centered_style)
    elements.append(header)
    elements.append(company_info)
    elements.append(Paragraph("<br/>", normal_style))  # Spacer
    
    # Client/Service Information
    service_info = [
        ['Order ID', service.id],
        ['Service Title', service.title],
        ['Service Description', service.description],
        ['Delivery Time', service.delivery_time],
        ['Support Duration', service.support_duration],
    ]
    service_table = Table(service_info, colWidths=[2*inch, 4*inch])
    service_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
    ]))
    elements.append(service_table)
    elements.append(Paragraph("<br/>", normal_style))  # Spacer
    
    # Financial Breakdown Section
    financial_data = [
        ['Service Cost', f"${service.cost:,.2f}"],
        ['Payment Status', service.payment_status],
        ['Order Status', service.order_status],
    ]
    
    financial_table = Table(financial_data, colWidths=[3*inch, 3*inch])
    financial_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
    ]))
    elements.append(financial_table)
    elements.append(Paragraph("<br/>", normal_style))  # Spacer
    
    # Footer Section: Terms and Legal
    footer = Paragraph(
        "Terms: All payments are due within 30 days of invoice. Late payments may incur a fee.",
        normal_style)
    footer_info = Paragraph("For any queries, contact us at ojjfred@gmail.com", centered_style)
    elements.append(footer)
    elements.append(footer_info)
    
    # Build the PDF
    doc.build(elements)

    buffer.seek(0)
    return buffer
