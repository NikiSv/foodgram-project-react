from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


def pdf_drawer(pdf, unit, ingredient_totals):
    pdfmetrics.registerFont(TTFont(
        'DejaVuSerif-Bold', 'DejaVuSerif-Bold.ttf'))
    pdf.setFont('DejaVuSerif-Bold', 14)
    pdf.drawString(100, 50, ' ')
    y = 670
    page_height = 800
    for name, total_amount in ingredient_totals.items():
        pdf.drawString(100, y, f'{name} ({unit}) - {total_amount} ')
        y -= 20
        if y < 50:
            pdf.showPage()
            y = page_height - 50
