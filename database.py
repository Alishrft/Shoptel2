import sqlite3
import threading
import time
import json
from config import DB_NAME
import jdatetime

db_lock = threading.Lock()


def get_connection():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.execute('PRAGMA journal_mode=WAL;')
    conn.row_factory = sqlite3.Row
    return conn


# ==============================
# 📂 بخش دسته‌بندی‌ها
# ==============================
def add_category(name):
    with db_lock:
        conn = get_connection()
        try:
            conn.execute("INSERT INTO categories (name) VALUES (?)", (name,)); conn.commit()
        except:
            pass
        conn.close()


def get_categories():
    conn = get_connection()
    res = conn.execute("SELECT * FROM categories").fetchall()
    conn.close()
    return [dict(r) for r in res]


def get_category_by_id(cid):
    conn = get_connection()
    res = conn.execute("SELECT * FROM categories WHERE id = ?", (cid,)).fetchone()
    conn.close()
    return dict(res) if res else None


def update_category(cat_id, name):
    with db_lock:
        conn = get_connection()
        conn.execute("UPDATE categories SET name = ? WHERE id = ?", (name, cat_id))
        conn.commit();
        conn.close()


def delete_category(cat_id):
    with db_lock:
        conn = get_connection()
        conn.execute("DELETE FROM categories WHERE id = ?", (cat_id,))
        conn.execute("UPDATE products SET category_id = NULL WHERE category_id = ?", (cat_id,))
        conn.commit();
        conn.close()


# ==============================
# 📦 بخش محصولات
# ==============================
def add_product(data):
    with db_lock:
        conn = get_connection()
        conn.execute("""INSERT INTO products (name, desc, price, stock, image_id, category_id, attributes)
                        VALUES (?, ?, ?, ?, ?, ?, ?)""",
                     (data['name'], data['desc'], data['price'], data['stock'], data['image'], data['cat_id'],
                      data.get('attrs', '')))
        conn.commit();
        conn.close()


def get_products(cat_id=None):
    conn = get_connection()
    if cat_id:
        res = conn.execute("SELECT * FROM products WHERE category_id = ? AND stock > 0", (cat_id,)).fetchall()
    else:
        res = conn.execute("SELECT * FROM products WHERE stock > 0").fetchall()
    conn.close()
    return [dict(r) for r in res]


def get_all_products_admin():
    conn = get_connection()
    res = conn.execute("SELECT * FROM products").fetchall()
    conn.close()
    return [dict(r) for r in res]


def get_product_by_id(pid):
    conn = get_connection()
    res = conn.execute("SELECT * FROM products WHERE id = ?", (pid,)).fetchone()
    conn.close()
    return dict(res) if res else None


def update_product_field(pid, field, value):
    with db_lock:
        conn = get_connection()
        conn.execute(f"UPDATE products SET {field} = ? WHERE id = ?", (value, pid))
        conn.commit();
        conn.close()


def update_product_image(pid, image_id):
    with db_lock:
        conn = get_connection()
        conn.execute("UPDATE products SET image_id = ? WHERE id = ?", (image_id, pid))
        conn.commit();
        conn.close()


def delete_product(pid):
    with db_lock:
        conn = get_connection()
        conn.execute("DELETE FROM products WHERE id = ?", (pid,))
        conn.execute("DELETE FROM product_variants WHERE product_id = ?", (pid,))  # حذف ویژگی‌ها همزمان
        conn.commit();
        conn.close()


# ==============================
# 🎨 بخش ویژگی‌ها (Variants)
# ==============================
def add_variant(pid, name, stock):
    with db_lock:
        conn = get_connection()
        conn.execute("INSERT INTO product_variants (product_id, name, stock) VALUES (?, ?, ?)", (pid, name, stock))
        # آپدیت موجودی کل محصول (جمع ویژگی‌ها)
        conn.execute("UPDATE products SET stock = stock + ? WHERE id = ?", (stock, pid))
        conn.commit();
        conn.close()


def get_variants(pid):
    conn = get_connection()
    res = conn.execute("SELECT * FROM product_variants WHERE product_id = ? AND stock > 0", (pid,)).fetchall()
    conn.close()
    return [dict(r) for r in res]


def get_variant_by_id(vid):
    conn = get_connection()
    res = conn.execute("SELECT * FROM product_variants WHERE id = ?", (vid,)).fetchone()
    conn.close()
    return dict(res) if res else None


def delete_variant(vid):
    with db_lock:
        conn = get_connection()
        var = conn.execute("SELECT product_id, stock FROM product_variants WHERE id = ?", (vid,)).fetchone()
        if var:
            # کسر از موجودی کل محصول قبل از حذف ویژگی
            conn.execute("UPDATE products SET stock = stock - ? WHERE id = ?", (var['stock'], var['product_id']))
            conn.execute("DELETE FROM product_variants WHERE id = ?", (vid,))
        conn.commit();
        conn.close()


def decrease_stock(items_json):
    """موجودی را کسر می‌کند و لیست کالاهای تمام شده را برمی‌گرداند"""
    if isinstance(items_json, str):
        items = json.loads(items_json)
    else:
        items = items_json

    finished_products = []
    with db_lock:
        conn = get_connection()
        for i in items:
            pid = i['product_id']
            qty = i['qty']
            vid = i.get('variant_id')  # ممکن است None باشد

            if vid and vid != 0:
                # کسر از ویژگی
                conn.execute("UPDATE product_variants SET stock = stock - ? WHERE id = ?", (qty, vid))
                # کسر از موجودی کل
                conn.execute("UPDATE products SET stock = stock - ? WHERE id = ?", (qty, pid))

                # چک کردن اتمام موجودی ویژگی
                res = conn.execute("SELECT name, stock FROM product_variants WHERE id = ?", (vid,)).fetchone()
                if res and res['stock'] <= 0:
                    finished_products.append(f"ویژگی: {res['name']}")
            else:
                # کسر از محصول ساده
                conn.execute("UPDATE products SET stock = stock - ? WHERE id = ?", (qty, pid))
                res = conn.execute("SELECT name, stock FROM products WHERE id = ?", (pid,)).fetchone()
                if res and res['stock'] <= 0:
                    finished_products.append(res['name'])

        conn.commit();
        conn.close()
    return finished_products


# ==============================
# ❤️ بخش علاقه‌مندی‌ها (Wishlist)
# ==============================
def toggle_wishlist(uid, pid):
    with db_lock:
        conn = get_connection()
        exist = conn.execute("SELECT * FROM wishlist WHERE user_id = ? AND product_id = ?", (uid, pid)).fetchone()
        if exist:
            conn.execute("DELETE FROM wishlist WHERE user_id = ? AND product_id = ?", (uid, pid))
            stat = False  # حذف شد
        else:
            conn.execute("INSERT INTO wishlist (user_id, product_id) VALUES (?, ?)", (uid, pid))
            stat = True  # اضافه شد
        conn.commit();
        conn.close()
    return stat


def get_wishlist(uid):
    conn = get_connection()
    sql = "SELECT p.* FROM wishlist w JOIN products p ON w.product_id = p.id WHERE w.user_id = ?"
    res = conn.execute(sql, (uid,)).fetchall()
    conn.close()
    return [dict(r) for r in res]


# ==============================
# 🛒 بخش سبد خرید
# ==============================
def update_cart(user_id, pid, vid, change):
    """vid: شناسه ویژگی (اگر نباشد 0 یا None)"""
    with db_lock:
        conn = get_connection()

        # 1. تعیین موجودی انبار برای چک کردن
        if vid:
            stock_info = conn.execute("SELECT stock FROM product_variants WHERE id = ?", (vid,)).fetchone()
        else:
            stock_info = conn.execute("SELECT stock FROM products WHERE id = ?", (pid,)).fetchone()

        # 2. پیدا کردن آیتم در سبد (با احتساب ویژگی)
        if vid:
            curr = conn.execute("SELECT qty FROM cart WHERE user_id=? AND product_id=? AND variant_id=?",
                                (user_id, pid, vid)).fetchone()
        else:
            curr = conn.execute(
                "SELECT qty FROM cart WHERE user_id=? AND product_id=? AND (variant_id IS NULL OR variant_id=0)",
                (user_id, pid)).fetchone()

        current_qty = curr['qty'] if curr else 0
        new_qty = current_qty + change

        msg = "✅";
        success = True

        if not stock_info:
            msg = "نامعتبر";
            success = False
        elif new_qty > stock_info['stock']:
            msg = "موجودی ناکافی";
            success = False
        elif new_qty <= 0:
            if vid:
                conn.execute("DELETE FROM cart WHERE user_id=? AND product_id=? AND variant_id=?", (user_id, pid, vid))
            else:
                conn.execute(
                    "DELETE FROM cart WHERE user_id=? AND product_id=? AND (variant_id IS NULL OR variant_id=0)",
                    (user_id, pid))
            msg = "حذف شد"
        else:
            if curr:
                if vid:
                    conn.execute("UPDATE cart SET qty=? WHERE user_id=? AND product_id=? AND variant_id=?",
                                 (new_qty, user_id, pid, vid))
                else:
                    conn.execute(
                        "UPDATE cart SET qty=? WHERE user_id=? AND product_id=? AND (variant_id IS NULL OR variant_id=0)",
                        (new_qty, user_id, pid))
            else:
                conn.execute("INSERT INTO cart (user_id, product_id, variant_id, qty) VALUES (?, ?, ?, ?)",
                             (user_id, pid, vid if vid else 0, new_qty))
            msg = "افزوده شد"

        conn.commit();
        conn.close()
        return success, msg


def get_cart(user_id):
    conn = get_connection()
    # دریافت نام محصول و نام ویژگی (اگر باشد)
    sql = """
    SELECT c.qty, c.variant_id, p.name, p.price, p.id as product_id, v.name as var_name
    FROM cart c
    JOIN products p ON c.product_id = p.id
    LEFT JOIN product_variants v ON c.variant_id = v.id
    WHERE c.user_id = ?
    """
    res = conn.execute(sql, (user_id,)).fetchall()
    conn.close()
    return [dict(r) for r in res]


def clear_cart(user_id):
    with db_lock:
        conn = get_connection()
        conn.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))
        conn.commit();
        conn.close()


# ==============================
# 👤 بخش کاربران و تنظیمات
# ==============================
def save_user_info(user_id, info):
    with db_lock:
        conn = get_connection()
        conn.execute("INSERT OR REPLACE INTO users (id, name, phone, address, postal) VALUES (?, ?, ?, ?, ?)",
                     (user_id, info['name'], info['phone'], info['address'], info['postal']))
        conn.commit();
        conn.close()


def get_user_info(user_id):
    conn = get_connection()
    res = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(res) if res else {}


def get_all_users():
    conn = get_connection()
    res = conn.execute("SELECT * FROM users").fetchall()
    conn.close()
    return [dict(r) for r in res]


# ==============================
# 📝 بخش سفارشات
# ==============================
def save_order(user_id, details, items, total, method, tracking="", status="Pending", receipt="", discount=0):
    oid = f"ORD-{int(time.time())}"
    # تبدیل تاریخ به شمسی
    date = jdatetime.datetime.now().strftime("%Y/%m/%d %H:%M")
    items_json = json.dumps(items)
    with db_lock:
        conn = get_connection()
        # اضافه شدن discount به اینسرت
        conn.execute("INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                     (oid, user_id, details, items_json, total, discount, date, tracking, status, method, receipt))
        conn.commit(); conn.close()
    return oid

def update_order_status(oid, status, tracking=""):
    with db_lock:
        conn = get_connection()
        conn.execute("UPDATE orders SET status = ?, tracking_code = ? WHERE order_id = ?", (status, tracking, oid))
        conn.commit();
        conn.close()


def get_all_orders():
    conn = get_connection()
    res = conn.execute("SELECT * FROM orders ORDER BY date DESC").fetchall()
    conn.close()
    return [dict(r) for r in res]


def get_user_orders(user_id):
    conn = get_connection()
    res = conn.execute("SELECT * FROM orders WHERE user_id = ? ORDER BY date DESC", (user_id,)).fetchall()
    conn.close()
    return [dict(r) for r in res]


def get_order_by_id(oid):
    conn = get_connection()
    res = conn.execute("SELECT * FROM orders WHERE order_id = ?", (oid,)).fetchone()
    conn.close()
    return dict(res) if res else None


def get_last_order_by_user(user_id):
    conn = get_connection()
    res = conn.execute("SELECT * FROM orders WHERE user_id = ? ORDER BY date DESC LIMIT 1", (user_id,)).fetchone()
    conn.close()
    return dict(res) if res else None


# --- تنظیمات ---
def get_setting(key, default=None):
    conn = get_connection()
    res = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    conn.close()
    return res['value'] if res else default


def set_setting(key, value):
    with db_lock:
        conn = get_connection()
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
        conn.commit();
        conn.close()


# --- جستجو ---
def search_products(query, sort_by="newest"):
    conn = get_connection()
    sql = "SELECT * FROM products WHERE name LIKE ? OR desc LIKE ?"
    if sort_by == "price_asc":
        sql += " ORDER BY price ASC"
    elif sort_by == "price_desc":
        sql += " ORDER BY price DESC"
    else:
        sql += " ORDER BY id DESC"

    res = conn.execute(sql, (f"%{query}%", f"%{query}%")).fetchall()
    conn.close()
    return [dict(r) for r in res]

# ... (تمام کدهای قبلی database.py را حفظ کنید، فقط این بخش‌ها را به آخرش اضافه کنید) ...

# --- کدهای تخفیف ---


def add_coupon(code, type, value, min_order, limit):
    with db_lock:
        conn = get_connection()
        conn.execute("INSERT OR REPLACE INTO coupons VALUES (?, ?, ?, ?, 0, ?)", (code, type, value, min_order, limit))
        conn.commit(); conn.close()

def get_coupons_list():
    conn = get_connection()
    res = conn.execute("SELECT * FROM coupons").fetchall()
    conn.close()
    return [dict(r) for r in res]

def delete_coupon(code):
    with db_lock:
        conn = get_connection()
        conn.execute("DELETE FROM coupons WHERE code = ?", (code,))
        conn.commit(); conn.close()

def get_coupon(code):
    conn = get_connection()
    res = conn.execute("SELECT * FROM coupons WHERE code = ?", (code,)).fetchone()
    conn.close()
    return dict(res) if res else None

def is_coupon_used(user_id, code):
    conn = get_connection()
    res = conn.execute("SELECT * FROM used_coupons WHERE user_id = ? AND code = ?", (user_id, code)).fetchone()
    conn.close()
    return True if res else False

def use_coupon(user_id, code):
    with db_lock:
        conn = get_connection()
        # ثبت استفاده کاربر
        conn.execute("INSERT OR IGNORE INTO used_coupons VALUES (?, ?)", (user_id, code))
        # افزایش شمارنده
        conn.execute("UPDATE coupons SET used_count = used_count + 1 WHERE code = ?", (code,))
        conn.commit(); conn.close()