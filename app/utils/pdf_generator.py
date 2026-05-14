from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
import os

def create_loan_details_pdf(loan_rows, file_path):
    styles = getSampleStyleSheet()
    elements = []

    # Title
    title = Paragraph("Customer Loan Details Report", styles["Title"])
    elements.append(title)
    elements.append(Spacer(1, 0.3 * inch))

    data = [[
        "Customer Name",
        "Loan Amount (₹)",
        "EMI (₹)",
        "Loan Number",
        "Next Due Date",
        "Branch Name",
        "Branch Phone"
    ]]

    for loan in loan_rows:
        data.append([
            loan.get("customerName", ""),
            f"{loan.get('loanAmount', 0):,.0f}",
            f"{loan.get('emiAndPreEmi', 0):,.0f}",
            loan.get("loanNumber", ""),
            loan.get("nextPaymentDueDate", ""),
            loan.get("branchName", ""),
            loan.get("branchPhoneNo", "")
        ])

    table = Table(data, repeatRows=1)

    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ]))

    elements.append(table)

    doc = SimpleDocTemplate(file_path, pagesize=A4)
    doc.build(elements)
