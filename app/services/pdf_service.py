"""
PDF generation (docs/01 §2 / §8): every document (receipt, payslip,
certificate) is built in-memory from DB truth and streamed — never written to
disk, never given a stored URL. Serverless has no writable disk anyway, and
regenerating from data means a fixed bug re-renders old documents correctly.
"""

import calendar

import qrcode
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas as pdf_canvas
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


def generate_payslip(payslip_data: Dict[str, Any]) -> BytesIO:
    """
    Generate a PDF payslip for a payroll record (in-memory, streamed).

    payslip_data keys:
        institution_name, institution_address, institution_phone,
        staff_name, position, month (1-12), year,
        days_present, days_half, daily_rate, total_amount, generated_at
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5 * inch, bottomMargin=0.5 * inch)
    elements = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'PayslipTitle', parent=styles['Heading1'], fontSize=22,
        textColor=colors.HexColor('#1e40af'), spaceAfter=6,
        alignment=TA_CENTER, fontName='Helvetica-Bold',
    )
    subtitle_style = ParagraphStyle(
        'PayslipSubtitle', parent=styles['Normal'], fontSize=11,
        textColor=colors.HexColor('#64748b'), spaceAfter=20, alignment=TA_CENTER,
    )
    heading_style = ParagraphStyle(
        'PayslipHeading', parent=styles['Heading2'], fontSize=14,
        textColor=colors.HexColor('#334155'), spaceAfter=10, spaceBefore=10,
        fontName='Helvetica-Bold',
    )

    elements.append(Paragraph(payslip_data.get('institution_name', ''), title_style))
    institution_info = (
        f"{payslip_data.get('institution_address', '')}<br/>"
        f"{payslip_data.get('institution_phone', '')}"
    )
    elements.append(Paragraph(institution_info, subtitle_style))

    month_name = calendar.month_name[payslip_data['month']]
    elements.append(Paragraph(
        f"<b>PAYSLIP — {month_name} {payslip_data['year']}</b>", heading_style,
    ))
    elements.append(Spacer(1, 0.2 * inch))

    label_value_style = TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#475569')),
        ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#0f172a')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ])

    staff_info = [
        ['Staff Name:', payslip_data['staff_name']],
        ['Position:', payslip_data.get('position') or '—'],
        ['Pay Period:', f"{month_name} {payslip_data['year']}"],
    ]
    generated_at = payslip_data.get('generated_at')
    if generated_at is not None:
        formatted = generated_at.strftime('%d %B %Y') if hasattr(generated_at, 'strftime') else str(generated_at)
        staff_info.append(['Generated On:', formatted])
    staff_table = Table(staff_info, colWidths=[2 * inch, 4 * inch])
    staff_table.setStyle(label_value_style)
    elements.append(staff_table)
    elements.append(Spacer(1, 0.3 * inch))

    elements.append(Paragraph("Earnings", heading_style))
    daily_rate = float(payslip_data.get('daily_rate') or 0)
    days_present = payslip_data.get('days_present') or 0
    days_half = payslip_data.get('days_half') or 0
    total_amount = float(payslip_data.get('total_amount') or 0)
    earnings = [
        ['Description', 'Days', 'Rate', 'Amount'],
        ['Full days', str(days_present), f"₹{daily_rate:,.2f}",
         f"₹{days_present * daily_rate:,.2f}"],
        ['Half days', str(days_half), f"₹{daily_rate / 2:,.2f}",
         f"₹{days_half * daily_rate * 0.5:,.2f}"],
        ['NET PAY', '', '', f"₹{total_amount:,.2f}"],
    ]
    earnings_table = Table(earnings, colWidths=[2.2 * inch, 1 * inch, 1.2 * inch, 1.6 * inch])
    earnings_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e40af')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f1f5f9')),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
    ]))
    elements.append(earnings_table)
    elements.append(Spacer(1, 0.4 * inch))

    note_style = ParagraphStyle(
        'PayslipNote', parent=styles['Normal'], fontSize=8,
        textColor=colors.HexColor('#94a3b8'), alignment=TA_CENTER,
    )
    elements.append(Paragraph(
        "This is a computer-generated payslip and does not require a signature.",
        note_style,
    ))

    doc.build(elements)
    buffer.seek(0)
    return buffer


def _qr_image(data: str) -> ImageReader:
    """Render `data` as a QR code usable by reportlab (in-memory PNG)."""
    qr = qrcode.QRCode(box_size=8, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    png = BytesIO()
    img.save(png, format="PNG")
    png.seek(0)
    return ImageReader(png)


def generate_certificate(cert_data: Dict[str, Any]) -> BytesIO:
    """
    Generate a course-completion certificate PDF (in-memory, streamed).
    Rendered entirely from DB data; the verification_code is embedded as a QR
    pointing at the public verify URL.

    cert_data keys:
        institution_name, student_name, course_name, certificate_number,
        issue_date, verification_code, verify_url
    """
    buffer = BytesIO()
    page_size = landscape(A4)
    width, height = page_size
    c = pdf_canvas.Canvas(buffer, pagesize=page_size)

    # Border (double rule)
    c.setStrokeColor(colors.HexColor('#1e40af'))
    c.setLineWidth(3)
    c.rect(0.4 * inch, 0.4 * inch, width - 0.8 * inch, height - 0.8 * inch)
    c.setLineWidth(1)
    c.rect(0.5 * inch, 0.5 * inch, width - 1.0 * inch, height - 1.0 * inch)

    # Institution name
    c.setFillColor(colors.HexColor('#1e40af'))
    c.setFont('Helvetica-Bold', 26)
    c.drawCentredString(width / 2, height - 1.4 * inch, cert_data.get('institution_name', ''))

    # Title
    c.setFillColor(colors.HexColor('#334155'))
    c.setFont('Helvetica-Bold', 20)
    c.drawCentredString(width / 2, height - 2.2 * inch, 'CERTIFICATE OF COMPLETION')

    c.setFillColor(colors.HexColor('#64748b'))
    c.setFont('Helvetica', 13)
    c.drawCentredString(width / 2, height - 2.8 * inch, 'This is to certify that')

    # Student name
    c.setFillColor(colors.HexColor('#0f172a'))
    c.setFont('Helvetica-Bold', 24)
    c.drawCentredString(width / 2, height - 3.4 * inch, cert_data['student_name'])

    c.setFillColor(colors.HexColor('#64748b'))
    c.setFont('Helvetica', 13)
    c.drawCentredString(width / 2, height - 3.95 * inch, 'has successfully completed the course')

    # Course name
    c.setFillColor(colors.HexColor('#1e40af'))
    c.setFont('Helvetica-Bold', 18)
    c.drawCentredString(width / 2, height - 4.5 * inch, cert_data['course_name'])

    # Certificate number + issue date (bottom-left)
    issue_date = cert_data.get('issue_date')
    issue_str = issue_date.strftime('%d %B %Y') if hasattr(issue_date, 'strftime') else str(issue_date or '')
    c.setFillColor(colors.HexColor('#475569'))
    c.setFont('Helvetica', 10)
    c.drawString(0.9 * inch, 1.5 * inch, f"Certificate No: {cert_data['certificate_number']}")
    c.drawString(0.9 * inch, 1.25 * inch, f"Issue Date: {issue_str}")
    c.drawString(0.9 * inch, 1.0 * inch, f"Verification Code: {cert_data['verification_code']}")

    # QR code (bottom-right) — scan to verify authenticity
    qr_size = 1.1 * inch
    c.drawImage(
        _qr_image(cert_data['verify_url']),
        width - 0.9 * inch - qr_size, 0.9 * inch,
        qr_size, qr_size,
    )
    c.setFont('Helvetica', 8)
    c.setFillColor(colors.HexColor('#94a3b8'))
    c.drawCentredString(width - 0.9 * inch - qr_size / 2, 0.72 * inch, 'Scan to verify')

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer
