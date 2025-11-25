from telegram import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

WEBAPP_URL = "https://shoptel2.onrender.com"


def main_menu(is_admin=False):
    btns = [
        # دکمه وب اپ
        [InlineKeyboardButton("🛍 باز کردن فروشگاه (Mini App)", web_app=WebAppInfo(url=WEBAPP_URL))],

        # دکمه سبد خرید حذف شد (چون داخل مینی اپ هست)
        # فقط دکمه پیگیری و پشتیبانی ماند
        [InlineKeyboardButton("📦 سوابق سفارشات", callback_data="history"),
         InlineKeyboardButton("📞 پشتیبانی", callback_data="support")]
    ]
    if is_admin:
        btns.append([InlineKeyboardButton("⚙️ ورود به پنل مدیریت", callback_data="admin_menu")])
    return InlineKeyboardMarkup(btns)

def admin_menu():
    btns = [
        [InlineKeyboardButton("📊 گزارشات", callback_data="admin_reports"), InlineKeyboardButton("📥 خروجی اکسل", callback_data="download_excel")], # دکمه اکسل
        [InlineKeyboardButton("📦 مدیریت محصولات", callback_data="mng_prods"), InlineKeyboardButton("🎟 کدهای تخفیف", callback_data="manage_coupons")], # دکمه تخفیف
        [InlineKeyboardButton("📂 دسته‌ها", callback_data="mng_cats"), InlineKeyboardButton("⚙️ تنظیمات", callback_data="settings")],
        [InlineKeyboardButton("📢 ارسال همگانی", callback_data="broadcast"), InlineKeyboardButton("👥 مشتریان", callback_data="users_list")],
        [InlineKeyboardButton("🔙 خروج", callback_data="start")]
    ]
    return InlineKeyboardMarkup(btns)
def settings_menu():
    btns = [
        [InlineKeyboardButton("💳 کارت به کارت", callback_data="set_card_info"), InlineKeyboardButton("📞 متن پشتیبانی", callback_data="set_support_text")],
        [InlineKeyboardButton("🚚 هزینه پست", callback_data="set_ship"), InlineKeyboardButton("🔒 قفل کانال", callback_data="set_lock")],
        [InlineKeyboardButton("🔑 مرچنت زرین‌پال", callback_data="set_merchant"), InlineKeyboardButton("📢 تنظیم کانال", callback_data="set_channel_id")],
        [InlineKeyboardButton("🌐 سوئیچ پرداخت آنلاین", callback_data="set_pay"), InlineKeyboardButton("🔙 بازگشت", callback_data="admin_menu")]
    ]
    return InlineKeyboardMarkup(btns)

def user_action_menu(user_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✉️ ارسال پیام", callback_data=f"msg_user_{user_id}")],
        [InlineKeyboardButton("🚚 ارسال کد رهگیری", callback_data=f"track_user_{user_id}")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="users_list")]
    ])

def manage_products_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ افزودن محصول", callback_data="add_prod")],
        [InlineKeyboardButton("✏️ ویرایش/حذف محصول", callback_data="edit_prod_list")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_menu")]
    ])


def manage_cats_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ افزودن دسته", callback_data="new_cat")],
        [InlineKeyboardButton("✏️ ویرایش نام دسته", callback_data="edit_cat_list")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_menu")]
    ])

def edit_cat_opts(cid):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ تغییر نام", callback_data=f"edcatren_{cid}"), InlineKeyboardButton("🗑 حذف دسته", callback_data=f"edcatdel_{cid}")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="edit_cat_list")]
    ])

def cart_controls(pid, qty):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕", callback_data=f"inc_{pid}"), InlineKeyboardButton(f"{qty}", callback_data="n"), InlineKeyboardButton("➖", callback_data=f"dec_{pid}")],
        [InlineKeyboardButton("🗑 حذف", callback_data=f"del_{pid}")]
    ])

def cart_checkout():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ تکمیل خرید", callback_data="checkout")],
        [InlineKeyboardButton("🗑 خالی کردن", callback_data="clear_cart"), InlineKeyboardButton("🔙 منو", callback_data="start")]
    ])


def back(target="start"):
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data=target)]])

def product_btns(pid, is_liked=False):
    heart = "❤️" if is_liked else "🤍"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ افزودن به سبد", callback_data=f"add_{pid}")],
        [InlineKeyboardButton(f"{heart}", callback_data=f"like_{pid}"), InlineKeyboardButton("🛒 سبد", callback_data="cart")],
        [InlineKeyboardButton("🔙 لیست", callback_data="cats")]
    ])

def wishlist_menu():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="start")]])

def edit_product_opts(pid):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ نام", callback_data=f"ed_name_{pid}"), InlineKeyboardButton("✏️ قیمت", callback_data=f"ed_price_{pid}")],
        [InlineKeyboardButton("✏️ موجودی کل", callback_data=f"ed_stock_{pid}"), InlineKeyboardButton("🎨 ویژگی‌ها (رنگ/سایز)", callback_data=f"mng_var_{pid}")],
        [InlineKeyboardButton("🖼 عکس", callback_data=f"ed_img_{pid}"), InlineKeyboardButton("🗑 حذف", callback_data=f"ed_del_{pid}")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="mng_prods")]
    ])
