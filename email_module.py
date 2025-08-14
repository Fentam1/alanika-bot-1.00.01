import os
import smtplib
import tempfile
from email.message import EmailMessage
from typing import Dict, Any
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.lib import colors

# Регистрируем шрифт с кириллицей
pdfmetrics.registerFont(TTFont('DejaVuSans', 'DejaVuSans.ttf'))

def generate_pdf(order: Dict[str, Any]) -> str:
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    tmp_name = tmp.name
    tmp.close()

    doc = SimpleDocTemplate(tmp_name)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Russian', fontName='DejaVuSans', fontSize=10, leading=12))
    styles.add(ParagraphStyle(name='Header', fontName='DejaVuSans', fontSize=16, alignment=1, spaceAfter=15))

    elements = []
    elements.append(Paragraph("Заказ", styles['Header']))

    # Информация о заказе
    order_info = [
        ["Менеджер:", order.get('manager', '')],
        ["Клиент:", order.get('client', '')],
        ["Дата доставки:", order.get('delivery_date', '')],
        ["Адрес:", order.get('delivery_address', '')],
        ["Примечание:", order.get('note', '')],
    ]
    info_table = Table(order_info, colWidths=[100, 400])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'DejaVuSans'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 15))

    # Таблица товаров с extra_code
    table_data = [["Код", "Товар", "Название", "Кол-во", "Без PVN", "C PVN", "Сумма(€)"]]
    total_sum = 0
    for item in order.get('products', []):
        extra_code = item.get('extra_code', '')

        # Считаем сумму с НДС
        try:
            sum_with_vat = float(item.get('price_with_vat', 0)) * int(item.get('qty', 0))
        except ValueError:
            sum_with_vat = 0

        item['sum_with_vat'] = sum_with_vat
        total_sum += sum_with_vat

        table_data.append([
            item.get('code', 'N/A'),
            extra_code,
            item.get('name', 'Без названия'),
            item.get('qty', 0),
            item.get('price_no_vat', ''),
            item.get('price_with_vat', ''),
            f"{sum_with_vat:.2f}"
        ])

    product_table = Table(table_data, colWidths=[90, 40, 300, 30, 35, 35, 40])
    product_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'DejaVuSans'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4A90E2')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (3, 1), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.lightgrey])
    ]))
    elements.append(product_table)
    elements.append(Spacer(1, 15))

    elements.append(Paragraph(f"<b>Общая сумма заказа:</b> {total_sum:.2f} €", styles['Russian']))

    doc.build(elements)
    return tmp_name


def send_email_with_pdf(order: Dict[str, Any], sender: str, password: str, recipient: str):
    pdf_path = None
    try:
        pdf_path = generate_pdf(order)

        msg = EmailMessage()
        msg['Subject'] = f"Новый заказ от {order.get('manager','')}"
        msg['From'] = sender
        msg['To'] = recipient

        # Текстовая версия
        plain_lines = [
            "Новый заказ!",
            f"Менеджер: {order.get('manager','')}",
            f"Клиент: {order.get('client','')}",
            f"Дата доставки: {order.get('delivery_date','')}",
            f"Адрес: {order.get('delivery_address','')}",
            f"Примечание: {order.get('note','')}",
            "",
            "Товары:"
        ]
        for p in order.get('products', []):
            plain_lines.append(f"{p.get('code','N/A')} | {p.get('extra_code','')} | {p.get('name','')[:45]:45} | {p.get('qty',0)}")
        msg.set_content("\n".join(plain_lines))

        # HTML версия
        product_rows = "".join(
            f"<tr><td>{p.get('code','N/A')}</td><td>{p.get('extra_code','')}</td><td>{p.get('name','')}</td><td style='text-align:center'>{p.get('qty',0)}</td></tr>"
            for p in order.get('products', [])
        )
        html = f"""
        <html>
          <body>
            <h2>📦 Новый заказ от менеджера {order.get('manager','')}</h2>
            <p><strong>Клиент:</strong> {order.get('client','')}<br>
               <strong>Адрес:</strong> {order.get('delivery_address','')}<br>
               <strong>Дата:</strong> {order.get('delivery_date','')}<br>
               <strong>Примечание:</strong> {order.get('note','')}</p>
            <h3>Состав заказа:</h3>
            <table border="1" cellpadding="6" cellspacing="0" style="border-collapse: collapse;">
              <tr style="background:#f2f2f2;"><th>Код</th><th>Товар</th><th>Название</th><th>Кол-во</th></tr>
              {product_rows}
            </table>
          </body>
        </html>
        """
        msg.add_alternative(html, subtype="html")

        # Прикрепляем PDF
        with open(pdf_path, "rb") as f:
            msg.add_attachment(f.read(), maintype="application", subtype="pdf", filename="order.pdf")

        # Отправка письма
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(sender, password)
            smtp.send_message(msg)

        print("📨 Email с PDF отправлен успешно")

    except Exception as e:
        print("❌ Ошибка при отправке письма:", e)
        raise
    finally:
        if pdf_path and os.path.exists(pdf_path):
            os.remove(pdf_path)
