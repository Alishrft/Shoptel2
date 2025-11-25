import json

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
import database as db
import keyboards as kb
import utils
from config import ADMIN_ID
from main import GET_COUPON

NAME, PHONE, ADDRESS, POSTAL, PAY_METHOD = range(5)
SEARCH_QUERY = 20

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ... (همان کد قبلی)
    user_id = update.effective_user.id
    if update.callback_query:
        await update.callback_query.answer()
        try:
            await update.callback_query.message.delete()
        except:
            pass
    if db.get_setting('force_join') == 'True':
        chan = db.get_setting('channel_id')
        try:
            stat = await context.bot.get_chat_member(chan, user_id)
            if stat.status in ['left', 'kicked']:
                await context.bot.send_message(user_id, f"⛔️ عضویت الزامی:\n{chan}", reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("عضو شدم", callback_data="start")]]))
                return
        except:
            pass
    await context.bot.send_message(user_id, "🌹 خوش آمدید", reply_markup=kb.main_menu(user_id == ADMIN_ID))


# --- پشتیبانی (خواندن از دیتابیس) ---
async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # متن پیش‌فرض اگر تنظیم نشده باشد
    default_text = "📞 برای ارتباط با پشتیبانی به آیدی ادمین پیام دهید."
    text = db.get_setting('support_text', default_text)
    await update.callback_query.edit_message_text(f"📞 **پشتیبانی:**\n\n{text}", reply_markup=kb.back("start"),
                                                  parse_mode='Markdown')


async def view_cats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    cats = db.get_categories()
    if not cats: await update.callback_query.edit_message_text("خالی", reply_markup=kb.back("start")); return
    btns = [[InlineKeyboardButton(c['name'], callback_data=f"cat_{c['id']}")] for c in cats]
    btns.append([InlineKeyboardButton("🔙", callback_data="start")])
    await update.callback_query.edit_message_text("📂 انتخاب:", reply_markup=InlineKeyboardMarkup(btns))


async def view_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    cid = update.callback_query.data.split('_')[1]
    prods = db.get_products(cid)
    if not prods: await update.callback_query.answer("خالی", show_alert=True); return
    try:
        await update.callback_query.message.delete()
    except:
        pass
    for p in prods:
        txt = f"🛍 **{p['name']}**\n📝 {p['desc']}\n💰 {p['price']:,} ت\n📦 موجودی: {p['stock']}"
        mk = kb.product_btns(p['id'])
        if p['image_id']:
            await context.bot.send_photo(update.effective_user.id, p['image_id'], caption=txt, reply_markup=mk,
                                         parse_mode='Markdown')
        else:
            await context.bot.send_message(update.effective_user.id, txt, reply_markup=mk, parse_mode='Markdown')


async def add_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pid = int(update.callback_query.data.split('_')[1])
    ok, msg = db.update_cart(update.effective_user.id, pid, 1)
    await update.callback_query.answer(msg, show_alert=not ok)


async def view_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    items = db.get_cart(uid)
    if not items:
        if update.callback_query: await update.callback_query.answer("سبد خالی", True)
        return
    try:
        await update.callback_query.message.delete()
    except:
        pass
    await context.bot.send_message(uid, "🛒 **سبد خرید:**", parse_mode='Markdown')
    t = 0
    for i in items:
        t += i['price'] * i['qty']
        await context.bot.send_message(uid, f"🔸 {i['name']}\n{i['qty']} عدد | فی: {i['price']:,}",
                                       reply_markup=kb.cart_controls(i['product_id'], i['qty']))
    s = int(db.get_setting('shipping_cost', 0))
    await context.bot.send_message(uid, f"📦 پست: {s:,}\n💵 جمع: {t + s:,}", reply_markup=kb.cart_checkout())

    items = db.get_cart_extended(uid)  # تابع جدید
    # ...
    for i in items:
        # نمایش نام ویژگی
        var_txt = f" ({i['variant_name']})" if i['variant_name'] else ""
        txt = f"🔸 **{i['name']}**{var_txt}\n..."


async def modify_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    act, pid = update.callback_query.data.split('_')
    if act == 'inc':
        db.update_cart(update.effective_user.id, int(pid), 1)
    elif act == 'dec':
        db.update_cart(update.effective_user.id, int(pid), -1)
    elif act == 'del':
        db.update_cart(update.effective_user.id, int(pid), -1000)
    if not db.get_cart(update.effective_user.id):
        await clear_cart_handler(update, context)
    else:
        await view_cart(update, context)


async def clear_cart_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db.clear_cart(update.effective_user.id)
    try:
        await update.callback_query.message.delete()
    except:
        pass
    await context.bot.send_message(update.effective_user.id, "🗑 خالی شد.",
                                   reply_markup=kb.main_menu(update.effective_user.id == ADMIN_ID))


async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    o = db.get_user_orders(update.effective_user.id)
    t = "📦 **سوابق:**\n" + "\n".join([f"🔹 {x['date']} | {x['status']}" for x in o]) if o else "خالی"
    await update.callback_query.edit_message_text(t, reply_markup=kb.back("start"), parse_mode='Markdown')


async def start_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    u = db.get_user_info(query.from_user.id)
    if u.get('name'):
        context.user_data.update(u)
        await query.message.reply_text(
            f"📋 **اطلاعات ارسال قبلی شما:**\n\n👤 {u['name']}\n📞 {u['phone']}\n📍 {u['address']}\n📮 {u['postal']}\n\nآیا از همین اطلاعات استفاده می‌کنید؟",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ بله، تایید است", callback_data="yes"),
                 InlineKeyboardButton("✏️ خیر، ویرایش اطلاعات", callback_data="no")]
            ]),
            parse_mode='Markdown'
        )
        return POSTAL  # پرش به مرحله آخر

    await query.message.reply_text("👤 **نام و نام خانوادگی** خود را وارد کنید:\n(لغو: /cancel)", parse_mode='Markdown')
    return NAME


async def get_new(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.edit_message_text("👤 **نام و نام خانوادگی** جدید را وارد کنید:")
    return NAME


async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['name'] = update.message.text.strip()
    await update.message.reply_text("📞 **شماره تماس** را وارد کنید:")
    return PHONE


async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.text.strip()
    # تبدیل اعداد فارسی
    phone = phone.replace('۰', '0').replace('۱', '1').replace('۲', '2').replace('۳', '3').replace('۴', '4').replace('۵',
                                                                                                                    '5').replace(
        '۶', '6').replace('۷', '7').replace('۸', '8').replace('۹', '9')
    context.user_data['phone'] = phone
    await update.message.reply_text("📍 **آدرس دقیق** پستی:")
    return ADDRESS


async def get_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['address'] = update.message.text.strip()
    await update.message.reply_text("📮 **کد پستی** (۱۰ رقمی):")
    return POSTAL


async def get_postal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        postal = update.message.text.strip()
        postal = postal.replace('۰', '0').replace('۱', '1').replace('۲', '2').replace('۳', '3').replace('۴',
                                                                                                        '4').replace(
            '۵', '5').replace('۶', '6').replace('۷', '7').replace('۸', '8').replace('۹', '9')
        context.user_data['postal'] = postal

    # ذخیره اطلاعات کاربر
    db.save_user_info(update.effective_user.id, context.user_data)

    # --- محاسبه و ذخیره مبلغ کل (رفع باگ شما) ---
    uid = update.effective_user.id
    items = db.get_cart(uid)
    if not items:
        msg_func = update.message.reply_text if update.message else update.callback_query.message.reply_text
        await msg_func("سبد خرید شما خالی است.", reply_markup=kb.back("start"))
        return ConversationHandler.END

    cart_total = sum([i['price'] * i['qty'] for i in items])
    shipping = int(db.get_setting('shipping_cost', 0))

    # بررسی سقف ارسال رایگان
    free_limit = int(db.get_setting('free_shipping_limit', '999999999'))
    if cart_total >= free_limit:
        shipping = 0

    total_with_shipping = cart_total + shipping

    # ⚠️ مهم: ذخیره مبلغ در حافظه برای استفاده در کد تخفیف
    context.user_data['raw_total'] = total_with_shipping
    context.user_data['discount'] = 0  # ریست کردن تخفیف قبلی

    # نمایش منوی پرداخت
    await show_payment_menu(update, context, total_with_shipping, 0)
    return PAY_METHOD


async def show_payment_menu(update, context, total, discount=0):
    final_amount = total - discount
    if final_amount < 1000: final_amount = 1000

    btns = [[InlineKeyboardButton("💳 کارت به کارت", callback_data="card")]]
    if db.get_setting('payment_online') == 'active':
        btns.append([InlineKeyboardButton("🌐 پرداخت آنلاین (زرین‌پال)", callback_data="online")])

    if discount == 0:
        btns.append([InlineKeyboardButton("🎟 کد تخفیف دارم", callback_data="ask_coupon")])
    else:
        btns.append([InlineKeyboardButton(f"✅ تخفیف: {discount:,} تومان (حذف)", callback_data="remove_coupon")])

    btns.append([InlineKeyboardButton("🔙 بازگشت به سبد خرید", callback_data="cart_back")])

    txt = f"💳 **مرحله نهایی و پرداخت**\n\n💵 مبلغ کل: {total:,} تومان"
    if discount > 0:
        txt += f"\n🎁 تخفیف: {discount:,} تومان"
    txt += f"\n\n💰 **قابل پرداخت: {final_amount:,} تومان**\n\n👇 روش پرداخت را انتخاب کنید:"

    if update.callback_query:
        await update.callback_query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(btns),
                                                      parse_mode='Markdown')
    else:
        await update.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(btns), parse_mode='Markdown')


# --- لاجیک کد تخفیف ---
from main import GET_COUPON  # ایمپورت وضعیت


async def process_pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    d = update.callback_query.data

    # هندلرهای جانبی داخل همین state
    if d == "cart_back":
        await view_cart(update, context)
        return ConversationHandler.END
    if d == "remove_coupon":
        return await remove_coupon(update, context)
    if d == "back_to_pay":
        return await back_to_pay_handler(update, context)

    # شروع پرداخت اصلی
    uid = update.effective_user.id
    items = db.get_cart(uid)

    # محاسبه نهایی
    raw_total = context.user_data.get('raw_total')
    discount = context.user_data.get('discount', 0)
    final_amount = raw_total - discount
    if final_amount < 1000: final_amount = 1000

    # ذخیره برای استفاده در زرین پال یا فیش
    context.user_data['zp_amt'] = final_amount

    if d == "card":
        c = db.get_setting('card_info', 'تنظیم نشده')
        await update.callback_query.edit_message_text(
            f"💳 **شماره کارت:**\n`{c}`\n\n💰 مبلغ قابل پرداخت: **{final_amount:,} تومان**\n\n📸 لطفاً مبلغ را واریز کرده و **عکس فیش** را همینجا ارسال کنید.",
            parse_mode='Markdown'
        )
        # اینجا تخفیف را مصرف میکنیم (یا میتونیم بذاریم بعد از تایید فیش)
        if discount > 0:
            code = context.user_data.get('coupon_code')
            db.use_coupon(uid, code)

        return ConversationHandler.END

    elif d == "online":
        await update.callback_query.edit_message_text("⏳ در حال اتصال به درگاه...")
        res, url, auth = utils.zarinpal_request(final_amount, context.user_data.get('phone'))

        if res:
            context.user_data.update({'zp_auth': auth})
            # ثبت سفارش موقت
            oid = db.save_order(uid, context.user_data['name'], items, final_amount, "Online", "", "Pending Pay")
            context.user_data['zp_oid'] = oid

            # مصرف کد تخفیف
            if discount > 0:
                code = context.user_data.get('coupon_code')
                db.use_coupon(uid, code)

            keyboard = [[InlineKeyboardButton("🔗 ورود به درگاه پرداخت", url=url)],
                        [InlineKeyboardButton("🔄 بررسی وضعیت پرداخت", callback_data="check_zp")],
                        [InlineKeyboardButton("🔙 انصراف", callback_data="cart_back")]]
            await update.callback_query.edit_message_text(f"🔗 لینک پرداخت ساخته شد.\nمبلغ: {final_amount:,} تومان",
                                                          reply_markup=InlineKeyboardMarkup(keyboard),
                                                          parse_mode='Markdown')
        else:
            await update.callback_query.edit_message_text(f"❌ خطا: {url}", reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔙 بازگشت", callback_data="cart_back")]]))
            return PAY_METHOD

    return ConversationHandler.END


async def check_zp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    auth = context.user_data.get('zp_auth')
    oid_temp = context.user_data.get('zp_oid')  # آیدی سفارش موقت

    if not auth:
        await query.answer("اطلاعات یافت نشد", show_alert=True)
        return

    await query.answer("⏳ در حال استعلام...")

    # استعلام مبلغ پرداختی (مبلغ نهایی با کسر تخفیف)
    final_amount = context.user_data.get('zp_amt')
    res, ref = utils.zarinpal_verify(auth, final_amount)

    if res:
        # دریافت اطلاعات برای ثبت نهایی
        uid = update.effective_user.id
        cart = db.get_cart(uid)
        u = db.get_user_info(uid)
        user_det = f"{u.get('name', 'ناشناس')}\n{u.get('phone', '-')}\n{u.get('address', '-')}\n{u.get('postal', '-')}"

        # دریافت تخفیف
        discount = context.user_data.get('discount', 0)

        # آماده‌سازی لیست آیتم‌ها
        items_to_save = []
        for i in cart:
            items_to_save.append({
                "product_id": i['product_id'],
                "variant_id": i['variant_id'],
                "name": i['name'],
                "var_name": i.get('var_name', ""),
                "qty": i['qty'],
                "price": i['price']
            })

        # آپدیت وضعیت سفارش موقت یا ثبت جدید
        # چون قبلا save_order کردیم (Pending Pay)، الان باید تکمیلش کنیم
        # اما چون تابع save_order ما تغییر کرده (discount گرفته)، بهتره سفارش قبلی رو آپدیت کنیم
        # یا یه سفارش جدید تایید شده بسازیم. برای سادگی و دقت، سفارش جدید ثبت میکنیم و قبلی رو نادیده میگیریم (یا حذف میکنیم)

        # ثبت سفارش نهایی (Paid)
        final_oid = db.save_order(uid, user_det, items_to_save, f"{final_amount:,}", "Online", ref, "Paid", "",
                                  discount)

        # مصرف کد تخفیف
        if discount > 0:
            code = context.user_data.get('coupon_code')
            if code: db.use_coupon(uid, code)

        # کسر موجودی
        import json
        finished = db.decrease_stock(json.dumps(items_to_save))
        db.clear_cart(uid)

        # تولید فاکتور
        order_data = db.get_order_by_id(final_oid)
        path = utils.generate_invoice_html(order_data)

        # پیام به کاربر
        await query.edit_message_text(f"✅ **پرداخت موفق!**\nرهگیری: `{ref}`\nشماره سفارش: `{final_oid}`",
                                      parse_mode='Markdown')

        back_home = InlineKeyboardMarkup([[InlineKeyboardButton("🏠 بازگشت به فروشگاه", callback_data="start")]])
        await context.bot.send_document(uid, open(path, 'rb'), caption="📄 فاکتور خرید شما", reply_markup=back_home)

        # پیام به ادمین
        msg = f"💰 **فروش آنلاین جدید!**\nمبلغ: {final_amount:,} تومان\nسفارش: `{final_oid}`"
        if finished: msg += "\n⚠️ **اتمام موجودی:**\n" + "\n".join(finished)

        await context.bot.send_document(ADMIN_ID, open(path, 'rb'), caption=msg, parse_mode='Markdown')

        # پاکسازی حافظه
        context.user_data['zp_auth'] = None
    else:
        await query.answer("❌ پرداخت انجام نشد یا ناموفق بود.", show_alert=True)


async def search_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.edit_message_text("🔍 نام محصول مورد نظر را بنویسید:", reply_markup=kb.back("start"))
    return SEARCH_QUERY


async def perform_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text
    context.user_data['search_q'] = query

    # پیش‌فرض: جدیدترین
    products = db.search_products(query, "newest")

    if not products:
        await update.message.reply_text("❌ محصولی یافت نشد.", reply_markup=kb.back("start"))
        return ConversationHandler.END

    await update.message.reply_text(f"🔍 نتایج جستجو برای '{query}':\n(برای تغییر مرتب‌سازی از دکمه‌ها استفاده کنید)",
                                    reply_markup=kb.search_sort_btns())

    # نمایش نتایج (تابع کمکی)
    await show_product_list(update, context, products)
    return ConversationHandler.END


async def sort_results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sort_mode = update.callback_query.data.split('_')[1] + "_" + update.callback_query.data.split('_')[2]
    q = context.user_data.get('search_q', '')
    products = db.search_products(q, sort_mode)

    await update.callback_query.answer("مرتب شد")
    await update.callback_query.message.delete()  # پاک کردن لیست قبلی
    await show_product_list(update, context, products)
    # دوباره دکمه‌های مرتب‌سازی را نشان بده
    await context.bot.send_message(update.effective_chat.id, "⚙️ فیلترها:", reply_markup=kb.search_sort_btns())


async def show_product_list(update, context, products):
    chat_id = update.effective_chat.id
    w_list = db.get_wishlist(chat_id)
    w_ids = [p['id'] for p in w_list]  # لیست آیدی‌های لایک شده

    for p in products:
        # میانگین امتیاز
        stars = "⭐️" * int(p['avg_rating']) if p['avg_rating'] else "هنوز امتیازی ثبت نشده"

        txt = f"🛍 **{p['name']}**\n📝 {p['desc']}\n💰 {p['price']:,} ت\n📊 امتیاز: {stars}"
        is_liked = p['id'] in w_ids
        mk = kb.product_btns(p['id'], is_liked)

        if p['image_id']:
            await context.bot.send_photo(chat_id, p['image_id'], caption=txt, reply_markup=mk, parse_mode='Markdown')
        else:
            await context.bot.send_message(chat_id, txt, reply_markup=mk, parse_mode='Markdown')


# --- انتخاب ویژگی (Color & Size) ---
async def pre_add_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pid = int(update.callback_query.data.split('_')[1])
    variants = db.get_product_variants(pid)

    if variants:
        # اگر محصول ویژگی دارد (رنگ/سایز)، لیست را نشان بده
        await update.callback_query.edit_message_caption(caption="🎨 لطفاً **رنگ و سایز** (تنوع) را انتخاب کنید:",
                                                         reply_markup=kb.variant_btns(variants, pid))
    else:
        # اگر ندارد، مستقیم اضافه کن (مثل قبل)
        ok, msg = db.update_cart_variant(update.effective_user.id, pid, None, 1)
        await update.callback_query.answer(msg, show_alert=not ok)


async def add_variant_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = update.callback_query.data.split('_')
    pid = int(data[1])
    vid = int(data[2])

    ok, msg = db.update_cart_variant(update.effective_user.id, pid, vid, 1)
    await update.callback_query.answer(msg, show_alert=not ok)
    # برگرداندن دکمه به حالت عادی
    p = db.get_product_by_id(pid)
    mk = kb.product_btns(pid, False)  # وضعیت لایک را باید دوباره چک کرد ولی فعلا فالس
    await update.callback_query.edit_message_caption(caption=f"🛍 **{p['name']}**\n💰 {p['price']:,} ت\n✅ افزوده شد.",
                                                     reply_markup=mk, parse_mode='Markdown')


# --- علاقه‌مندی‌ها ---
async def toggle_like(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pid = int(update.callback_query.data.split('_')[1])
    status = db.toggle_wishlist(update.effective_user.id, pid)
    msg = "❤️ به علاقه‌مندی‌ها اضافه شد" if status else "💔 حذف شد"
    await update.callback_query.answer(msg)

    # آپدیت دکمه (قلب پر یا خالی)
    await update.callback_query.edit_message_reply_markup(reply_markup=kb.product_btns(pid, status))


async def view_wishlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    prods = db.get_wishlist(update.effective_user.id)
    if not prods:
        await update.callback_query.edit_message_text("❤️ لیست علاقه‌مندی شما خالی است.", reply_markup=kb.back("start"))
        return

    await update.callback_query.message.delete()
    await context.bot.send_message(update.effective_chat.id, "❤️ **لیست علاقه‌مندی‌های شما:**", parse_mode='Markdown')
    await show_product_list(update, context, prods)


# --- هندلر داده‌های مینی‌اپ ---
async def handle_webapp_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        # 1. دریافت جیسون از مینی‌اپ
        raw_data = update.effective_message.web_app_data.data
        items = json.loads(raw_data)  # [{'id': '101', 'qty': 2}, ...]
    except:
        return

    if not items: return

    # 2. خالی کردن سبد قدیمی و پر کردن با دیتای جدید
    db.clear_cart(user_id)

    total_price = 0
    final_items = []

    for item in items:
        pid = int(item['id'])
        qty = int(item['qty'])

        # اعتبارسنجی قیمت از دیتابیس (امنیت)
        prod = db.get_product_by_id(pid)
        if prod and prod['stock'] >= qty:
            db.update_cart(user_id, pid, qty)  # افزودن به سبد دیتابیس
            total_price += int(prod['price']) * qty
            final_items.append(f"🔸 {prod['name']} (x{qty})")

    if not final_items:
        await update.message.reply_text("❌ خطا: موجودی محصولات تغییر کرده است.")
        return

    # 3. نمایش فاکتور و دکمه تکمیل
    shipping = int(db.get_setting('shipping_cost', 0))
    final_amount = total_price + shipping

    msg = "✅ **سفارش شما دریافت شد!**\n\n" + "\n".join(final_items)
    msg += f"\n\n💰 مبلغ کالاها: {total_price:,} تومان"
    msg += f"\n🚚 هزینه پست: {shipping:,} تومان"
    msg += f"\n💵 **قابل پرداخت: {final_amount:,} تومان**"

    # هدایت به مرحله چک‌اوت
    await update.message.reply_text(msg, reply_markup=kb.cart_checkout(), parse_mode='Markdown')


# --- هندلر کد تخفیف ---
async def apply_coupon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text("🎟 لطفاً **کد تخفیف** خود را ارسال کنید:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 انصراف", callback_data="back_to_pay")]]))
    return GET_COUPON


async def check_coupon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = update.message.text.strip()
    user_id = update.effective_user.id

    # بازیابی مبلغ خام (که در get_postal ذخیره کردیم)
    raw_total = context.user_data.get('raw_total', 0)

    if raw_total == 0:
        # اگر به هر دلیلی مبلغ نبود، دوباره محاسبه کن
        items = db.get_cart(user_id)
        cart_total = sum([i['price'] * i['qty'] for i in items])
        shipping = int(db.get_setting('shipping_cost', 0))
        raw_total = cart_total + shipping
        context.user_data['raw_total'] = raw_total

    # اعتبارسنجی کد
    coupon = db.get_coupon(code)

    if not coupon:
        await update.message.reply_text("❌ کد تخفیف نامعتبر است.", reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_pay")]]))
        return GET_COUPON

    if db.is_coupon_used(user_id, code):
        await update.message.reply_text("❌ شما قبلاً از این کد استفاده کرده‌اید.", reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_pay")]]))
        return GET_COUPON

    if coupon['used_count'] >= coupon['usage_limit']:
        await update.message.reply_text("❌ ظرفیت استفاده از این کد تمام شده است.", reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_pay")]]))
        return GET_COUPON

    if raw_total < coupon['min_order']:
        await update.message.reply_text(f"❌ حداقل خرید برای این کد {coupon['min_order']:,} تومان است.",
                                        reply_markup=InlineKeyboardMarkup(
                                            [[InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_pay")]]))
        return GET_COUPON

    # محاسبه مقدار تخفیف
    discount = 0
    if coupon['type'] == 'percent':
        discount = int(raw_total * coupon['value'] / 100)
    else:
        discount = coupon['value']

    context.user_data['discount'] = discount
    context.user_data['coupon_code'] = code

    await update.message.reply_text(f"✅ کد **{code}** اعمال شد!\n🎁 مبلغ {discount:,} تومان کسر گردید.")

    # نمایش مجدد منوی پرداخت
    await show_payment_menu(update, context, raw_total, discount)
    return PAY_METHOD


async def back_to_pay_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # بازگشت از صفحه ورود کد تخفیف به صفحه پرداخت (بدون تغییر تخفیف)
    raw_total = context.user_data.get('raw_total', 0)
    discount = context.user_data.get('discount', 0)
    await show_payment_menu(update, context, raw_total, discount)
    return PAY_METHOD


async def remove_coupon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # حذف کد تخفیف
    context.user_data['discount'] = 0
    context.user_data['coupon_code'] = None
    raw_total = context.user_data.get('raw_total', 0)
    await update.callback_query.answer("کد تخفیف حذف شد")
    await show_payment_menu(update, context, raw_total, 0)
    return PAY_METHOD


