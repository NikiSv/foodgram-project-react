from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from rest_framework import status
from rest_framework.response import Response


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


def create_model_instance(request, instance, serializer_name):
    serializer = serializer_name(
        data={'user': request.user.id, 'recipe': instance.id, },
        context={'request': request})
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data, status=status.HTTP_201_CREATED)


def delete_model_instance(request, model_name, instance, error_message):
    if not model_name.objects.filter(user=request.user,
                                     recipe=instance).exists():
        return Response({'errors': error_message},
                        status=status.HTTP_400_BAD_REQUEST)
    model_name.objects.filter(user=request.user, recipe=instance).delete()
    return Response(status=status.HTTP_204_NO_CONTENT)
