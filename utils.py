

ZP_API_REQUEST = "https://sandbox.zarinpal.com/pg/v4/payment/request.json"
ZP_API_VERIFY = "https://sandbox.zarinpal.com/pg/v4/payment/verify.json"
ZP_API_STARTPAY = "https://sandbox.zarinpal.com/pg/StartPay/"

import requests
import json
import csv
import io
from datetime import datetime
import database as db
from config import ZARINPAL_MERCHANT_ID, CALLBACK_URL


# ... (توابع قبلی generate_html_report و generate_invoice_html و zarinpal سرجایشان باشند) ...

# --- تابع جدید: خروجی اکسل (CSV) ---
def generate_excel_report(orders):
    # استفاده از StringIO برای ساخت فایل در حافظه
    output = io.StringIO()
    writer = csv.writer(output)

    # هدر فایل
    writer.writerow(
        ['Order ID', 'Date', 'User ID', 'Name', 'Phone', 'Address', 'Total Price', 'Status', 'Payment Method', 'Items'])

    for o in orders:
        # تحلیل آیتم‌ها
        try:
            items = json.loads(o['items'])
        except:
            items = []
        items_str = " | ".join([f"{i['name']} ({i['qty']})" for i in items])

        # تحلیل مشخصات کاربر
        u_det = o['user_details'].split('\n')
        name = u_det[0] if len(u_det) > 0 else ""
        phone = u_det[1] if len(u_det) > 1 else ""
        addr = u_det[2] if len(u_det) > 2 else ""

        writer.writerow([o['order_id'], o['date'], o['user_id'], name, phone, addr, o['total_price'], o['status'],
                         o['payment_method'], items_str])

    return output.getvalue().encode('utf-8-sig')  # انکدینگ برای نمایش صحیح فارسی در اکسل
def generate_html_report(data, report_type="orders"):
    style = """<style>body{font-family:Tahoma;direction:rtl;text-align:right;background:#f4f4f4;padding:20px}table{width:100%;border-collapse:collapse;background:#fff}th,td{padding:10px;border:1px solid #ddd;text-align:center}th{background:#333;color:#fff}</style>"""
    html = f"<html><head><meta charset='utf-8'>{style}</head><body><h2>گزارش</h2><table><tr><th>کد</th><th>مشتری</th><th>مبلغ</th><th>وضعیت</th><th>تاریخ</th></tr>"
    for row in data:
        det = row['user_details'].split('\n')[0] if row['user_details'] else "ناشناس"
        html += f"<tr><td>{row['order_id']}</td><td>{det}</td><td>{row['total_price']}</td><td>{row['status']}</td><td>{row['date']}</td></tr>"
    html += "</table></body></html>"
    filename = f"report_{int(datetime.now().timestamp())}.html"
    with open(filename, "w", encoding="utf-8") as f: f.write(html)
    return filename


def generate_invoice_html(order):
    try:
        items = json.loads(order['items'])
    except:
        items = []

    # استخراج اطلاعات مشتری
    details = order['user_details'].split('\n')
    name = details[0] if len(details) > 0 else "ناشناس"
    phone = details[1] if len(details) > 1 else "-"
    address = details[2] if len(details) > 2 else "-"
    postal = details[3] if len(details) > 3 else "-"

    rows = ""
    for i, item in enumerate(items):
        v_name = f"<span class='variant'>{item.get('var_name')}</span>" if item.get('var_name') else ""
        rows += f"""
        <tr>
            <td>{i + 1}</td>
            <td class="item-name">{item['name']} {v_name}</td>
            <td>{item['qty']}</td>
            <td>{item['price']:,}</td>
            <td>{item['price'] * item['qty']:,}</td>
        </tr>
        """

    # استایل حرفه‌ای فاکتور
    style = """
    <style>
        @import url('https://cdn.jsdelivr.net/gh/rastikerdar/vazir-font/dist/font-face.css');
        body { font-family: 'Vazir', Tahoma, sans-serif; direction: rtl; background: #f0f2f5; padding: 20px; margin: 0; }
        .invoice-box { max-width: 800px; margin: auto; background: #fff; padding: 40px; border-radius: 16px; box-shadow: 0 5px 20px rgba(0,0,0,0.05); }
        .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #f0f0f0; padding-bottom: 20px; margin-bottom: 30px; }
        .logo h1 { margin: 0; color: #2c3e50; font-size: 24px; }
        .meta { text-align: left; color: #7f8c8d; font-size: 13px; line-height: 1.6; }

        .info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 30px; }
        .info-box { background: #f8f9fa; padding: 20px; border-radius: 12px; border: 1px solid #eee; }
        .info-title { font-weight: bold; color: #34495e; margin-bottom: 10px; display: block; border-bottom: 1px solid #e0e0e0; padding-bottom: 5px; }
        .info-line { margin-bottom: 5px; font-size: 14px; color: #555; }

        table { width: 100%; border-collapse: collapse; margin-bottom: 30px; }
        th { background: #34495e; color: #fff; padding: 15px; font-weight: normal; font-size: 14px; }
        td { padding: 15px; border-bottom: 1px solid #eee; color: #333; font-size: 14px; }
        tr:nth-child(even) { background-color: #fcfcfc; }
        .item-name { font-weight: bold; }
        .variant { font-size: 11px; background: #eef2f3; color: #555; padding: 2px 6px; border-radius: 4px; margin-right: 5px; }

        .total-section { display: flex; justify-content: flex-end; }
        .total-box { background: #2c3e50; color: #fff; padding: 20px; border-radius: 12px; width: 250px; }
        .total-line { display: flex; justify-content: space-between; margin-bottom: 10px; font-size: 14px; opacity: 0.9; }
        .final-total { display: flex; justify-content: space-between; font-size: 18px; font-weight: bold; border-top: 1px solid rgba(255,255,255,0.2); padding-top: 10px; margin-top: 10px; }

        .footer { text-align: center; margin-top: 50px; color: #aaa; font-size: 12px; border-top: 1px solid #eee; padding-top: 20px; }
    </style>
    """

    html = f"""
    <!DOCTYPE html>
    <html lang="fa">
    <head><meta charset="utf-8">{style}</head>
    <body>
        <div class="invoice-box">
            <div class="header">
                <div class="logo"><h1>فاکتور فروش</h1></div>
                <div class="meta">
                    تاریخ: {order['date']}<br>
                    شماره سفارش: {order['order_id']}<br>
                    وضعیت: {order['status']}
                </div>
            </div>

            <div class="info-grid">
                <div class="info-box">
                    <span class="info-title">مشخصات خریدار</span>
                    <div class="info-line">👤 نام: {name}</div>
                    <div class="info-line">📞 تلفن: {phone}</div>
                </div>
                <div class="info-box">
                    <span class="info-title">آدرس ارسال</span>
                    <div class="info-line">📍 {address}</div>
                    <div class="info-line">📮 کد پستی: {postal}</div>
                </div>
            </div>

            <table>
                <thead>
                    <tr><th width="5%">#</th><th>شرح کالا</th><th width="10%">تعداد</th><th width="20%">فی (تومان)</th><th width="20%">مبلغ کل</th></tr>
                </thead>
                <tbody>{rows}</tbody>
            </table>

            <div class="total-section">
                <div class="total-box">
                    <div class="total-line"><span>جمع اقلام:</span><span>{int(str(order['total_price']).replace(',','')) + order['discount']:,}</span></div>
                    <div class="total-line"><span>هزینه ارسال:</span><span>{db.get_setting('shipping_cost','0')}</span></div>
                    
                    <div class="total-line" style="color: #e74c3c;"><span>تخفیف:</span><span>{order['discount']:,} -</span></div>
                    
                    <div class="final-total"><span>مبلغ نهایی:</span><span>{order['total_price']} تومان</span></div>
                </div>
            </div>

            <div class="footer">
                از اعتماد و خرید شما سپاسگزاریم ❤️
            </div>
        </div>
    </body>
    </html>
    """

    filename = f"Invoice_{order['order_id']}.html"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html)
    return filename


# ... (توابع زرین پال بدون تغییر) .


def zarinpal_request(amount, mobile):
    # 1. دریافت مرچنت کد
    merchant = db.get_setting('zarinpal_merchant')
    if not merchant or len(merchant) < 30:
        return False, "❌ کد درگاه تنظیم نشده است.", None

    # 2. تبدیل تومان به ریال
    amount_rial = int(amount) * 10
    if amount_rial < 1000:
        return False, "❌ مبلغ کمتر از حد مجاز (۱۰۰۰ ریال) است.", None

    data = {
        "merchant_id": merchant,
        "amount": amount_rial,
        "callback_url": CALLBACK_URL,
        "description": "خرید از ربات تلگرام",
        "metadata": {"mobile": mobile}
    }

    try:
        # ارسال درخواست به زرین‌پال
        response = requests.post(ZP_API_REQUEST, json=data, timeout=10)
        res = response.json()

        # چاپ خطا در کنسول برای عیب‌یابی
        if res['data']['code'] == 100:
            authority = res['data']['authority']
            url = f"{ZP_API_STARTPAY}{authority}"
            return True, url, authority
        else:
            print(f"⚠️ خطا در اتصال به زرین‌پال: {res}")
            return False, f"خطای زرین‌پال: {res['data']['code']}", None

    except Exception as e:
        print(f"⚠️ خطای شبکه درگاه: {e}")
        return False, "مشکل در اتصال به درگاه", None


def zarinpal_verify(authority, amount):
    merchant = db.get_setting('zarinpal_merchant')
    amount_rial = int(amount) * 10

    data = {
        "merchant_id": merchant,
        "amount": amount_rial,
        "authority": authority
    }

    try:
        response = requests.post(ZP_API_VERIFY, json=data, timeout=10)
        res = response.json()

        if res['data']['code'] == 100:
            return True, res['data']['ref_id']
        elif res['data']['code'] == 101:
            return True, res['data']['ref_id']  # قبلا تایید شده
        else:
            print(f"⚠️ خطای تایید پرداخت: {res}")
            return False, None
    except Exception as e:
        print(f"⚠️ خطا در وریفای: {e}")
        return False, None