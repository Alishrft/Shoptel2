import sqlite3
from config import DB_NAME


def setup():
    print("⏳ در حال ساخت دیتابیس و جداول...")
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # 1. جدول دسته‌بندی‌ها
    c.execute("CREATE TABLE IF NOT EXISTS categories (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT)")

    # 2. جدول محصولات (با ستون‌های جدید برای امتیاز و توضیحات)
    c.execute("""CREATE TABLE IF NOT EXISTS products (
                 id INTEGER PRIMARY KEY AUTOINCREMENT, 
                 name TEXT, 
                 desc TEXT, 
                 price INTEGER, 
                 stock INTEGER, 
                 image_id TEXT, 
                 category_id INTEGER, 
                 attributes TEXT,
                 avg_rating REAL DEFAULT 0
                 )""")

    # 3. جدول کاربران (ذخیره آدرس و مشخصات)
    c.execute("""CREATE TABLE IF NOT EXISTS users (
                 id INTEGER PRIMARY KEY, 
                 name TEXT, 
                 phone TEXT, 
                 address TEXT, 
                 postal TEXT
                 )""")

    # 4. جدول سبد خرید (با پشتیبانی از ویژگی محصول)
    c.execute("""CREATE TABLE IF NOT EXISTS cart (
                 user_id INTEGER, 
                 product_id INTEGER, 
                 variant_id INTEGER, 
                 qty INTEGER
                 )""")

    # 5. جدول سفارشات
    c.execute("""CREATE TABLE IF NOT EXISTS orders (
                     order_id TEXT PRIMARY KEY, 
                     user_id INTEGER, 
                     user_details TEXT, 
                     items TEXT, 
                     total_price TEXT, 
                     discount INTEGER,  
                     date TEXT, 
                     tracking_code TEXT, 
                     status TEXT, 
                     payment_method TEXT, 
                     receipt_link TEXT
                     )""")

    # 6. جدول تنظیمات ربات
    c.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")

    # 7. جدول ویژگی‌های محصول (رنگ/سایز) - جدید
    c.execute("""CREATE TABLE IF NOT EXISTS product_variants (
                 id INTEGER PRIMARY KEY AUTOINCREMENT, 
                 product_id INTEGER, 
                 name TEXT, 
                 stock INTEGER
                 )""")

    # 8. جدول علاقه‌مندی‌ها - جدید
    c.execute("""CREATE TABLE IF NOT EXISTS wishlist (
                 user_id INTEGER, 
                 product_id INTEGER, 
                 UNIQUE(user_id, product_id)
                 )""")

    # 9. جدول کدهای تخفیف - جدید
    c.execute("""CREATE TABLE IF NOT EXISTS coupons (
                 code TEXT PRIMARY KEY, 
                 type TEXT, 
                 value INTEGER, 
                 min_order INTEGER, 
                 used_count INTEGER, 
                 usage_limit INTEGER
                 )""")

    # 10. جدول کدهای استفاده شده (برای جلوگیری از استفاده مجدد) - جدید
    c.execute("""CREATE TABLE IF NOT EXISTS used_coupons (
                 user_id INTEGER, 
                 code TEXT, 
                 UNIQUE(user_id, code)
                 )""")

    # --- داده‌های پیش‌فرض ---
    # تنظیمات اولیه
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('shipping_cost', '0')")
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('payment_online', 'inactive')")
    c.execute(
        "INSERT OR IGNORE INTO settings (key, value) VALUES ('free_shipping_limit', '2000000')")  # ارسال رایگان بالای 2 میلیون
    c.execute(
        "INSERT OR IGNORE INTO settings (key, value) VALUES ('support_text', '📞 برای ارتباط با پشتیبانی به آیدی ادمین پیام دهید.')")

    # دسته‌بندی‌های تستی
    c.execute("INSERT OR IGNORE INTO categories (name) VALUES ('لباس مردانه')")
    c.execute("INSERT OR IGNORE INTO categories (name) VALUES ('لباس زنانه')")

    conn.commit()
    conn.close()
    print("✅ دیتابیس با موفقیت آپدیت و آماده شد.")


if __name__ == "__main__":
    setup()