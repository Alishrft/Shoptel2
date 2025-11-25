from flask import Flask, render_template, request, jsonify, send_file
import sqlite3
import requests
import io
import json
from config import DB_NAME, BOT_TOKEN, ADMIN_ID
import database as db
import utils

app = Flask(__name__)


@app.route('/img/<file_id>')
def get_image(file_id):
    try:
        info = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}").json()
        path = info['result']['file_path']
        img = requests.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{path}").content
        return send_file(io.BytesIO(img), mimetype='image/jpeg')
    except:
        return "", 404


@app.route('/')
def home():
    conn = sqlite3.connect(DB_NAME)
    cats = [{"id": c[0], "name": c[1]} for c in conn.execute("SELECT id, name FROM categories").fetchall()]

    p_rows = conn.execute(
        "SELECT id, name, price, image_id, desc, stock, category_id FROM products WHERE stock > 0").fetchall()
    products = []

    for r in p_rows:
        pid = r[0]
        v_rows = conn.execute("SELECT id, name, stock FROM product_variants WHERE product_id = ? AND stock > 0",
                              (pid,)).fetchall()
        variants = [{"id": v[0], "name": v[1], "stock": v[2]} for v in v_rows]

        img_link = f"/img/{r[3]}" if r[3] else "https://placehold.co/300x300?text=No+Image"

        products.append({
            "id": pid,
            "title": r[1],
            "price": r[2],
            "img": img_link,
            "desc": r[4] if r[4] else "",
            "stock": r[5],
            "cat_id": r[6],
            "variants": variants
        })
    conn.close()

    # ⚠️ تغییر مهم: ساخت JSON برای استفاده در مودال سبد خرید
    products_json = json.dumps(products)

    return render_template('index.html', categories=cats, products=products, products_json=products_json)


@app.route('/submit_order', methods=['POST'])
def submit_order():
    data = request.json
    uid = data.get('user_id')
    items_web = data.get('items')

    if not items_web: return jsonify({"status": "error", "message": "سبد خالی"})

    db.clear_cart(uid)

    items_for_db = []
    final_list_text = []
    total = 0

    for i in items_web:
        pid = int(i['id'])
        qty = int(i['qty'])
        vid = int(i.get('vid')) if i.get('vid') else 0

        ok, msg = db.update_cart(uid, pid, vid, qty)

        if ok:
            prod = db.get_product_by_id(pid)
            var_name = ""
            if vid:
                v = db.get_variant_by_id(vid)
                if v: var_name = v['name']

            price = int(prod['price'])
            total += price * qty

            items_for_db.append({
                "product_id": pid,
                "variant_id": vid,
                "name": prod['name'],
                "var_name": var_name,
                "qty": qty,
                "price": price
            })

            txt = f"🔸 {prod['name']}"
            if var_name: txt += f" ({var_name})"
            txt += f" - {qty} عدد"
            final_list_text.append(txt)

    if not items_for_db:
        return jsonify({"status": "error", "message": "موجودی کافی نیست"})

    ship = int(db.get_setting('shipping_cost', 0))

    # ساخت پیام تلگرام
    msg = "✅ **سفارش شما دریافت شد**\n\n" + "\n".join(final_list_text)
    msg += f"\n\n📦 پست: {ship:,}\n💵 **قابل پرداخت: {total + ship:,}**"

    # ذخیره موقت در دیتابیس (فقط سبد آپدیت شده کافیست، اما اگر بخواهید order بسازید همینجا میتوانید)
    # فعلا فقط پیام میدهیم تا کاربر در تلگرام پرداخت را انتخاب کند

    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
        "chat_id": uid, "text": msg, "parse_mode": "Markdown",
        "reply_markup": {"inline_keyboard": [[{"text": "✅ نهایی کردن و پرداخت", "callback_data": "checkout"}],
                                             [{"text": "🗑 لغو", "callback_data": "clear_cart"}]]}
    })
    return jsonify({"status": "success"})


if __name__ == '__main__':
    app.run(port=5000, debug=True)