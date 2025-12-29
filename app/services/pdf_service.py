from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from io import BytesIO
from datetime import datetime
from typing import Dict, Any


def generate_payment_receipt(payment_data: Dict[str, Any]) -> BytesIO:
    """
    Generate a PDF receipt for a payment

    Args:
        payment_data: Dictionary containing:
            - receipt_number: str
            - payment_date: date
            - student_name: str
            - course_name: str
            - total_fee: float
            - amount_paid: float
            - balance: float
            - payment_method: str
            - transaction_id: str (optional)
            - institution_name: str
            - institution_address: str
            - institution_phone: str
            - created_by_name: str

    Returns:
        BytesIO: PDF file as bytes
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)

    # Container for elements
    elements = []

    # Styles
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1e40af'),
        spaceAfter=6,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )

    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.HexColor('#64748b'),
        spaceAfter=20,
        alignment=TA_CENTER
    )

    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#334155'),
        spaceAfter=10,
        spaceBefore=10,
        fontName='Helvetica-Bold'
    )

    # Header - Institution Name
    institution_name = Paragraph(payment_data.get('institution_name', 'RAJTECH COMPUTER CENTER'), title_style)
    elements.append(institution_name)

    # Institution Address
    institution_info = f"{payment_data.get('institution_address', '')}<br/>{payment_data.get('institution_phone', '')}"
    institution_para = Paragraph(institution_info, subtitle_style)
    elements.append(institution_para)

    # Title - Payment Receipt
    receipt_title = Paragraph("<b>PAYMENT RECEIPT</b>", heading_style)
    elements.append(receipt_title)

    elements.append(Spacer(1, 0.2*inch))

    # Receipt Details Table
    receipt_info = [
        ['Receipt No:', payment_data['receipt_number']],
        ['Date:', payment_data['payment_date'].strftime('%d %B %Y') if hasattr(payment_data['payment_date'], 'strftime') else str(payment_data['payment_date'])],
    ]

    receipt_table = Table(receipt_info, colWidths=[2*inch, 4*inch])
    receipt_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#475569')),
        ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#0f172a')),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))

    elements.append(receipt_table)
    elements.append(Spacer(1, 0.3*inch))

    # Student & Course Details
    student_heading = Paragraph("Student Details", heading_style)
    elements.append(student_heading)

    student_info = [
        ['Student Name:', payment_data['student_name']],
        ['Course:', payment_data['course_name']],
    ]

    student_table = Table(student_info, colWidths=[2*inch, 4*inch])
    student_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#475569')),
        ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#0f172a')),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))

    elements.append(student_table)
    elements.append(Spacer(1, 0.3*inch))

    # Payment Details
    payment_heading = Paragraph("Payment Details", heading_style)
    elements.append(payment_heading)

    # Payment breakdown table
    payment_details = [
        ['Description', 'Amount'],
        ['Total Course Fee', f"₹{payment_data['total_fee']:,.2f}"],
        ['Amount Paid', f"₹{payment_data['amount_paid']:,.2f}"],
        ['Balance', f"₹{payment_data['balance']:,.2f}"],
    ]

    payment_table = Table(payment_details, colWidths=[3*inch, 2*inch])
    payment_table.setStyle(TableStyle([
        # Header row
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e40af')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('TOPPADDING', (0, 0), (-1, 0), 10),

        # Data rows
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('ALIGN', (1, 1), (1, -1), 'RIGHT'),

        # Grid
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),

        # Last row (Balance) - highlight
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f1f5f9')),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0, -1), (-1, -1), colors.HexColor('#0f172a')),
    ]))

    elements.append(payment_table)
    elements.append(Spacer(1, 0.3*inch))

    # Payment Method Details
    method_heading = Paragraph("Payment Method", heading_style)
    elements.append(method_heading)

    method_info = [
        ['Payment Method:', payment_data['payment_method'].upper()],
    ]

    # Add transaction ID if available
    if payment_data.get('transaction_id'):
        method_info.append(['Transaction ID:', payment_data['transaction_id']])

    method_table = Table(method_info, colWidths=[2*inch, 4*inch])
    method_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#475569')),
        ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#0f172a')),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))

    elements.append(method_table)
    elements.append(Spacer(1, 0.5*inch))

    # Footer - Signature area
    signature_style = ParagraphStyle(
        'Signature',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#64748b'),
        alignment=TA_RIGHT
    )

    footer_data = [
        [f"Received by: {payment_data.get('created_by_name', 'Staff')}", ''],
        ['', ''],
        ['_____________________', '_____________________'],
        ['Signature', 'Date'],
    ]

    footer_table = Table(footer_data, colWidths=[3*inch, 2*inch])
    footer_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#64748b')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, 0), 20),
        ('BOTTOMPADDING', (0, -2), (-1, -2), 2),
    ]))

    elements.append(footer_table)

    # Add note at bottom
    elements.append(Spacer(1, 0.3*inch))
    note_style = ParagraphStyle(
        'Note',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor('#94a3b8'),
        alignment=TA_CENTER,
        italic=True
    )
    note = Paragraph("This is a computer-generated receipt and does not require a signature.", note_style)
    elements.append(note)

    # Build PDF
    doc.build(elements)

    # Get PDF bytes
    buffer.seek(0)
    return buffer
