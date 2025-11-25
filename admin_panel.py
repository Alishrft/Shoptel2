from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
import database as db
import keyboards as kb
import utils
from config import ADMIN_ID
import io
import time
# States
NAME, DESC, PRICE, STOCK, CAT, PHOTO = range(6)
ADD_CAT = 10
SHIPPING_PRICE = 11
CARD_INFO = 12
EDIT_VAL = 13
EDIT_CAT_NAME = 14
SET_CHANNEL = 15
EDIT_PROD_IMG = 16
SET_MERCHANT = 17
SET_SUPPORT_TEXT = 18
SEND_USER_MSG = 19
SEND_USER_TRACK = 20
BROADCAST_MSG = 21
ADD_VAR_NAME = 22 # جدید
ADD_VAR_STOCK = 23 # جدید
ADD_COUPON_CODE, ADD_COUPON_VAL, ADD_COUPON_MIN = 30, 31, 32
async def admin_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("👑 **پنل مدیریت فروشگاه**", reply_markup=kb.admin_menu(), parse_mode='Markdown')


# --- لیست کاربران (جدید: کلیک‌خور) ---
async def user_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    users = db.get_all_users()
    if not users:
        await query.answer("لیست خالی است", show_alert=True)
        return

    btns = []
    for u in users[-15:]:  # نمایش 15 نفر آخر
        name = u.get('name', 'ناشناس')
        btns.append([InlineKeyboardButton(f"👤 {name} ({u['id']})", callback_data=f"manage_user_{u['id']}")])

    btns.append([InlineKeyboardButton("🔙 بازگشت", callback_data="admin_menu")])
    await query.edit_message_text("👥 برای عملیات روی کاربر کلیک کنید:", reply_markup=InlineKeyboardMarkup(btns))


async def manage_single_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.callback_query.data.split('_')[2]
    context.user_data['target_uid'] = uid
    u = db.get_user_info(uid)
    txt = f"👤 **کاربر:** {u.get('name')}\n📞 {u.get('phone')}\n📍 {u.get('address')}"
    await update.callback_query.edit_message_text(txt, reply_markup=kb.user_action_menu(uid), parse_mode='Markdown')


# --- ارسال پیام به کاربر ---
async def send_msg_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['target_uid'] = update.callback_query.data.split('_')[2]
    await update.callback_query.edit_message_text("✉️ پیام خود را بنویسید:")
    return SEND_USER_MSG


async def send_msg_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = context.user_data['target_uid']
    try:
        await context.bot.send_message(uid, f"🔔 **پیام از طرف مدیریت:**\n\n{update.message.text}",
                                       parse_mode='Markdown')
        await update.message.reply_text("✅ ارسال شد.", reply_markup=kb.admin_menu())
    except:
        await update.message.reply_text("❌ ارسال نشد (شاید ربات را بلاک کرده).", reply_markup=kb.admin_menu())
    return ConversationHandler.END


# --- ارسال کد رهگیری ---
async def send_track_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['target_uid'] = update.callback_query.data.split('_')[2]
    await update.callback_query.edit_message_text("🚚 کد رهگیری مرسوله را وارد کنید:")
    return SEND_USER_TRACK


async def send_track_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = context.user_data['target_uid']
    code = update.message.text

    # آپدیت آخرین سفارش کاربر
    last_order = db.get_last_order_by_user(uid)
    if last_order:
        db.update_order_status(last_order['order_id'], "ارسال شده", code)
        try:
            await context.bot.send_message(uid, f"🚚 **سفارش شما ارسال شد!**\n\n🔖 کد رهگیری: `{code}`",
                                           parse_mode='Markdown')
            await update.message.reply_text("✅ کد رهگیری ثبت و ارسال شد.", reply_markup=kb.admin_menu())
        except:
            await update.message.reply_text("✅ ثبت شد ولی کاربر ربات را بلاک کرده.", reply_markup=kb.admin_menu())
    else:
        await update.message.reply_text("❌ این کاربر سفارش فعالی ندارد.", reply_markup=kb.admin_menu())

    return ConversationHandler.END


# --- تنظیم متن پشتیبانی ---
async def set_support_text_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.edit_message_text("📝 متن جدید پشتیبانی (شماره، آیدی و...) را وارد کنید:")
    return SET_SUPPORT_TEXT


async def set_support_text_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db.set_setting('support_text', update.message.text)
    await update.message.reply_text("✅ متن پشتیبانی ذخیره شد.", reply_markup=kb.settings_menu())
    return ConversationHandler.END


# --- تایید/رد فیش (اصلاح دکمه بازگشت + موجودی) ---
async def handle_receipt_decision(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    act, oid, uid = q.data.split('_')

    # این دکمه حالا واقعاً کار میکند چون هندلرش در main.py هست
    back_admin = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به پنل", callback_data="admin_menu")]])

    if act == 'confirm':
        order = db.get_order_by_id(oid)
        if not order: await q.answer("یافت نشد"); return

        finished = db.decrease_stock(order['items'])
        db.update_order_status(oid, "تایید شده")

        path = utils.generate_invoice_html(order)
        try:
            await context.bot.send_document(uid, open(path, 'rb'), caption="✅ سفارش تایید شد.", parse_mode='Markdown')
        except:
            pass

        await context.bot.send_document(update.effective_chat.id, open(path, 'rb'), caption=f"فاکتور {oid}",
                                        parse_mode='Markdown')

        alert = "\n✅ تایید شد."
        if finished: alert += "\n⚠️ **اتمام موجودی:**\n" + "\n".join(finished)

        await q.edit_message_caption(q.message.caption + alert, parse_mode='Markdown')

    else:
        db.update_order_status(oid, "رد شده")
        try:
            await context.bot.send_message(uid, f"❌ سفارش `{oid}` رد شد.")
        except:
            pass
        await q.edit_message_caption(q.message.caption + "\n❌ رد شد", reply_markup=back_admin)


# --- بقیه توابع تنظیمات و محصول (مثل قبل) ---
async def manage_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    zp = "✅ فعال" if db.get_setting('payment_online') == 'active' else "❌ غیرفعال"
    lk = "✅ فعال" if db.get_setting('force_join') == 'True' else "❌ غیرفعال"
    sh = db.get_setting('shipping_cost', '0')

    text = f"⚙️ **تنظیمات:**\n\n💳 پرداخت آنلاین: {zp}\n🔒 قفل کانال: {lk}\n🚚 پست: {sh} تومان"
    try:
        await query.edit_message_text(text, reply_markup=kb.settings_menu(), parse_mode='Markdown')
    except:
        await query.message.reply_text(text, reply_markup=kb.settings_menu(), parse_mode='Markdown')


async def set_card_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    c = db.get_setting('card_info', '-')
    await update.callback_query.edit_message_text(f"💳 فعلی:\n`{c}`\n\nجدید:", parse_mode='Markdown')
    return CARD_INFO


async def set_card_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db.set_setting('card_info', update.message.text)
    await update.message.reply_text("✅ شد.", reply_markup=kb.settings_menu())
    return ConversationHandler.END


# (توابع set_shipping, set_channel, set_merchant مثل قبل...)
async def set_shipping_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.edit_message_text("🚚 هزینه پست:")
    return SHIPPING_PRICE


async def set_shipping_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        db.set_setting('shipping_cost', str(int(update.message.text))); await update.message.reply_text("✅ شد.",
                                                                                                        reply_markup=kb.admin_menu()); return ConversationHandler.END
    except:
        await update.message.reply_text("عدد!"); return SHIPPING_PRICE


async def set_channel_start(update: Update,
                            context: ContextTypes.DEFAULT_TYPE): await update.callback_query.edit_message_text(
    "📢 آیدی کانال:"); return SET_CHANNEL


async def set_channel_save(update: Update, context: ContextTypes.DEFAULT_TYPE): db.set_setting('channel_id',
                                                                                               update.message.text); await update.message.reply_text(
    "✅ شد.", reply_markup=kb.settings_menu()); return ConversationHandler.END


async def set_merchant_start(update: Update,
                             context: ContextTypes.DEFAULT_TYPE): await update.callback_query.edit_message_text(
    "🔑 مرچنت:"); return SET_MERCHANT


async def set_merchant_save(update: Update, context: ContextTypes.DEFAULT_TYPE): db.set_setting('zarinpal_merchant',
                                                                                                update.message.text); await update.message.reply_text(
    "✅ شد.", reply_markup=kb.settings_menu()); return ConversationHandler.END


async def toggle_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    curr = db.get_setting('payment_online')
    new_st = 'active' if curr != 'active' else 'inactive'
    db.set_setting('payment_online', new_st)
    msg = "✅ درگاه پرداخت روشن شد" if new_st == 'active' else "❌ درگاه پرداخت خاموش شد"
    await update.callback_query.answer(msg, show_alert=True) # آلرت واضح
    await manage_settings(update, context)


async def toggle_lock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    curr = db.get_setting('force_join')
    new_st = 'True' if curr != 'True' else 'False'
    db.set_setting('force_join', new_st)
    msg = "🔒 قفل کانال فعال شد" if new_st == 'True' else "🔓 قفل کانال غیرفعال شد"
    await update.callback_query.answer(msg, show_alert=True) # آلرت واضح
    await manage_settings(update, context)


# (توابع محصول و دسته مثل قبل)
async def manage_products(update: Update,
                          context: ContextTypes.DEFAULT_TYPE): await update.callback_query.edit_message_text(
    "📦 محصولات:", reply_markup=kb.manage_products_menu())


async def edit_prod_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = db.get_all_products_admin();
    b = [[InlineKeyboardButton(x['name'], callback_data=f"edit_p_{x['id']}")] for x in p];
    b.append([InlineKeyboardButton("🔙", callback_data="mng_prods")]);
    await update.callback_query.edit_message_text("انتخاب:", reply_markup=InlineKeyboardMarkup(b))


async def edit_prod_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pid = update.callback_query.data.split('_')[2];
    context.user_data['pid'] = pid;
    p = db.get_product_by_id(pid);
    await update.callback_query.edit_message_text(f"✏️ {p['name']}", reply_markup=kb.edit_product_opts(pid))


async def edit_prod_val_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    d = update.callback_query.data
    if 'ed_img_' in d: context.user_data['pid'] = d.split('_')[2]; await update.callback_query.edit_message_text(
        "عکس:"); return EDIT_PROD_IMG
    f = d.split('_')[1]
    if f == 'del': db.delete_product(context.user_data['pid']); await update.callback_query.answer(
        "حذف"); await manage_products(update, context); return ConversationHandler.END
    context.user_data['field'] = f;
    await update.callback_query.edit_message_text("مقدار:");
    return EDIT_VAL


async def edit_prod_val_save(update: Update, context: ContextTypes.DEFAULT_TYPE): db.update_product_field(
    context.user_data['pid'], context.user_data['field'], update.message.text); await update.message.reply_text("✅ شد.",
                                                                                                                reply_markup=kb.manage_products_menu()); return ConversationHandler.END


async def edit_prod_img_save(update: Update, context: ContextTypes.DEFAULT_TYPE): db.update_product_image(
    context.user_data['pid'], update.message.photo[-1].file_id); await update.message.reply_text("✅ شد.",
                                                                                                 reply_markup=kb.manage_products_menu()); return ConversationHandler.END


async def manage_cats(update: Update,
                      context: ContextTypes.DEFAULT_TYPE): c = db.get_categories(); m = "📂 دسته‌ها:\n" + "\n".join(
    [x['name'] for x in c]); await update.callback_query.edit_message_text(m, reply_markup=kb.manage_cats_menu())


async def edit_cat_list(update: Update, context: ContextTypes.DEFAULT_TYPE): c = db.get_categories(); b = [
    [InlineKeyboardButton(x['name'], callback_data=f"edcat_{x['id']}")] for x in c]; b.append(
    [InlineKeyboardButton("🔙", callback_data="mng_cats")]); await update.callback_query.edit_message_text("انتخاب:",
                                                                                                          reply_markup=InlineKeyboardMarkup(
                                                                                                              b))


async def edit_cat_select(update: Update, context: ContextTypes.DEFAULT_TYPE): cid = \
update.callback_query.data.split('_')[1]; context.user_data['cid'] = cid; await update.callback_query.edit_message_text(
    "عملیات:", reply_markup=kb.edit_cat_opts(cid))


async def edit_cat_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    act = update.callback_query.data.split('_')[0]
    if act == 'edcatdel':
        db.delete_category(update.callback_query.data.split('_')[1]); await update.callback_query.answer(
            "حذف"); await manage_cats(update, context); return ConversationHandler.END
    else:
        await update.callback_query.edit_message_text("نام:"); return EDIT_CAT_NAME


async def edit_cat_save(update: Update, context: ContextTypes.DEFAULT_TYPE): db.update_category(
    context.user_data['cid'], update.message.text); await update.message.reply_text("✅ شد.",
                                                                                    reply_markup=kb.manage_cats_menu()); return ConversationHandler.END


async def new_cat_start(update: Update,
                        context: ContextTypes.DEFAULT_TYPE): await update.callback_query.edit_message_text(
    "نام:"); return ADD_CAT


async def new_cat_save(update: Update, context: ContextTypes.DEFAULT_TYPE): db.add_category(
    update.message.text); await update.message.reply_text("✅ شد.",
                                                          reply_markup=kb.manage_cats_menu()); return ConversationHandler.END


async def add_prod_start(update: Update,
                         context: ContextTypes.DEFAULT_TYPE): await update.callback_query.edit_message_text(
    "نام:"); return NAME


async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE): context.user_data[
    'p_name'] = update.message.text; await update.message.reply_text("توضیحات:"); return DESC


async def get_desc(update: Update, context: ContextTypes.DEFAULT_TYPE): context.user_data[
    'p_desc'] = update.message.text; await update.message.reply_text("قیمت:"); return PRICE


async def get_price(update: Update, context: ContextTypes.DEFAULT_TYPE): context.user_data['p_price'] = int(
    update.message.text); await update.message.reply_text("موجودی:"); return STOCK


async def get_stock(update: Update, context: ContextTypes.DEFAULT_TYPE): context.user_data['p_stock'] = int(
    update.message.text); c = db.get_categories(); b = [[InlineKeyboardButton(x['name'], callback_data=str(x['id']))]
                                                        for x in c]; await update.message.reply_text("دسته:",
                                                                                                     reply_markup=InlineKeyboardMarkup(
                                                                                                         b)); return CAT


async def get_cat(update: Update, context: ContextTypes.DEFAULT_TYPE): context.user_data['p_cat'] = int(
    update.callback_query.data); await update.callback_query.edit_message_text("عکس:"); return PHOTO


async def get_photo(update: Update, context: ContextTypes.DEFAULT_TYPE): img = update.message.photo[
    -1].file_id if update.message.photo else None; d = context.user_data; db.add_product(
    {'name': d['p_name'], 'desc': d['p_desc'], 'price': d['p_price'], 'stock': d['p_stock'], 'cat_id': d['p_cat'],
     'image': img}); await update.message.reply_text("✅ شد.",
                                                     reply_markup=kb.admin_menu()); return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE): await update.message.reply_text("لغو.",
                                                                                                      reply_markup=kb.admin_menu()); return ConversationHandler.END


async def send_reports(update: Update, context: ContextTypes.DEFAULT_TYPE): await update.callback_query.answer(
    "⏳"); o = db.get_all_orders(); p = utils.generate_html_report(o); await context.bot.send_document(
    update.effective_chat.id, open(p, 'rb')); await context.bot.send_message(update.effective_chat.id, "منو:",
                                                                             reply_markup=kb.admin_menu())


# --- ارسال همگانی ---
async def broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        "📢 **ارسال پیام همگانی**\n\n"
        "لطفاً پیام خود را (متن، عکس، صدا یا...) ارسال کنید.\n"
        "این پیام برای تمام کاربرانی که تا به حال با ربات تعامل داشته‌اند ارسال می‌شود.\n\n"
        "❌ برای انصراف /cancel را بزنید.",
        parse_mode='Markdown'
    )
    return BROADCAST_MSG


async def broadcast_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # دریافت لیست تمام کاربران از دیتابیس
    users = db.get_all_users()

    if not users:
        await update.message.reply_text("❌ کاربری در دیتابیس یافت نشد.", reply_markup=kb.admin_menu())
        return ConversationHandler.END

    status_msg = await update.message.reply_text(f"⏳ در حال ارسال پیام به {len(users)} کاربر...\nلطفاً صبر کنید.")

    success_count = 0
    block_count = 0

    # گرفتن آیدی چت و آیدی پیام ادمین برای کپی کردن
    from_chat_id = update.message.chat_id
    message_id = update.message.message_id

    for user in users:
        try:
            # کپی کردن پیام برای کاربر
            await context.bot.copy_message(
                chat_id=user['id'],
                from_chat_id=from_chat_id,
                message_id=message_id
            )
            success_count += 1
        except Exception as e:
            # اگر کاربر ربات را بلاک کرده باشد یا اکانتش حذف شده باشد
            block_count += 1
            # (اختیاری: می‌توانید یک وقفه کوتاه برای جلوگیری از اسپم شدن بگذارید)
            # import asyncio; await asyncio.sleep(0.05)

    # گزارش نهایی
    report = (
        f"✅ **ارسال همگانی تمام شد!**\n\n"
        f"📤 کل تلاش: {len(users)}\n"
        f"✅ موفق: {success_count}\n"
        f"🚫 ناموفق (بلاک): {block_count}"
    )

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=report,
        reply_markup=kb.admin_menu(),
        parse_mode='Markdown'
    )
    return ConversationHandler.END


def edit_product_opts(pid):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ نام", callback_data=f"ed_name_{pid}"),
         InlineKeyboardButton("✏️ قیمت", callback_data=f"ed_price_{pid}")],
        [InlineKeyboardButton("✏️ موجودی کل", callback_data=f"ed_stock_{pid}"),
         InlineKeyboardButton("🎨 ویژگی‌ها (رنگ/سایز)", callback_data=f"mng_var_{pid}")],
        [InlineKeyboardButton("🖼 عکس", callback_data=f"ed_img_{pid}"),
         InlineKeyboardButton("🗑 حذف", callback_data=f"ed_del_{pid}")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="mng_prods")]
    ])


# --- مدیریت ویژگی‌ها (Variants) ---

async def manage_variants(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    # اگر از دکمه آمده، دیتا را بگیر، اگر از تابع داخلی آمده، از حافظه بگیر
    if hasattr(query, 'data') and 'mng_var_' in query.data:
        pid = query.data.split('_')[2]
        context.user_data['pid'] = pid
    else:
        pid = context.user_data.get('pid')

    vars = db.get_variants(pid)
    msg = "🎨 **مدیریت ویژگی‌ها:**\n\n"
    btns = []
    for v in vars:
        msg += f"▫️ {v['name']} (موجودی: {v['stock']})\n"
        btns.append([InlineKeyboardButton(f"🗑 حذف {v['name']}", callback_data=f"delvar_{v['id']}")])

    btns.append([InlineKeyboardButton("➕ افزودن ویژگی جدید", callback_data="add_var")])
    btns.append([InlineKeyboardButton("🔙 بازگشت به محصول", callback_data=f"edit_p_{pid}")])

    # اگر پیام قابل ویرایش است ویرایش کن، وگرنه پیام جدید بده (برای وقتی که از ادد میایم)
    try:
        await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(btns), parse_mode='Markdown')
    except:
        await query.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(btns), parse_mode='Markdown')


async def add_var_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.edit_message_text("📝 نام ویژگی را بنویسید (مثلاً: قرمز XL):")
    return ADD_VAR_NAME


async def get_var_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['v_name'] = update.message.text
    await update.message.reply_text("📦 موجودی این ویژگی:")
    return ADD_VAR_STOCK


async def get_var_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        stock = int(update.message.text)
        db.add_variant(context.user_data['pid'], context.user_data['v_name'], stock)
        await update.message.reply_text("✅ ویژگی اضافه شد.")
        # بازگشت به لیست ویژگی‌ها به جای منوی اصلی
        # اینجا باید یک آپدیت ساختگی درست کنیم یا مستقیم تابع را صدا بزنیم
        # راه ساده: ارسال پیام با دکمه مدیریت همین محصول
        pid = context.user_data['pid']
        markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 مدیریت ویژگی‌ها", callback_data=f"mng_var_{pid}")]])
        await update.message.reply_text("جهت ادامه مدیریت ویژگی‌ها:", reply_markup=markup)
        return ConversationHandler.END
    except:
        await update.message.reply_text("❌ عدد وارد کنید.")
        return ADD_VAR_STOCK


async def delete_variant(update: Update, context: ContextTypes.DEFAULT_TYPE):
    vid = update.callback_query.data.split('_')[1]
    db.delete_variant(vid)
    await update.callback_query.answer("حذف شد")
    await manage_variants(update, context)


async def download_excel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("⏳ در حال ساخت فایل...")

    orders = db.get_all_orders()
    if not orders:
        await query.edit_message_text("سفارشی وجود ندارد.", reply_markup=kb.admin_menu())
        return

    csv_data = utils.generate_excel_report(orders)

    # ارسال فایل
    await context.bot.send_document(
        chat_id=update.effective_chat.id,
        document=io.BytesIO(csv_data),
        filename=f"Orders_{int(time.time())}.csv",
        caption="📊 خروجی اکسل سفارشات"
    )
    await query.message.reply_text("منوی مدیریت:", reply_markup=kb.admin_menu())


# --- مدیریت تخفیف‌ها ---
async def manage_coupons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    coupons = db.get_coupons_list()

    msg = "🎟 **لیست کدهای تخفیف فعال:**\n\n"
    btns = []
    if not coupons: msg += "هیچ کدی تعریف نشده است."

    for c in coupons:
        type_icon = "%" if c['type'] == 'percent' else "تومان"
        msg += f"🔹 `{c['code']}` | {c['value']} {type_icon}\n   (استفاده: {c['used_count']}/{c['usage_limit']})\n"
        btns.append([InlineKeyboardButton(f"🗑 حذف {c['code']}", callback_data=f"del_coup_{c['code']}")])

    btns.append([InlineKeyboardButton("➕ ایجاد کد تخفیف جدید", callback_data="add_coupon")])
    btns.append([InlineKeyboardButton("🔙 بازگشت", callback_data="admin_menu")])

    try:
        await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(btns), parse_mode='Markdown')
    except:
        await query.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(btns), parse_mode='Markdown')


async def delete_coupon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = update.callback_query.data.split('_')[2]
    db.delete_coupon(code)
    await update.callback_query.answer("حذف شد")
    await manage_coupons(update, context)


# --- پروسه افزودن تخفیف ---
async def add_coupon_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.edit_message_text("📝 **کد تخفیف** را وارد کنید (مثلاً OFF1403):")
    return ADD_COUPON_CODE


async def get_coupon_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['c_code'] = update.message.text
    await update.message.reply_text("💰 **مقدار تخفیف** را وارد کنید:\n\nبرای درصد: `10%`\nبرای مبلغ ثابت: `50000`")
    return ADD_COUPON_VAL


async def get_coupon_val(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val = update.message.text
    if '%' in val:
        context.user_data['c_type'] = 'percent'
        context.user_data['c_val'] = int(val.replace('%', ''))
    else:
        context.user_data['c_type'] = 'fixed'
        context.user_data['c_val'] = int(val)

    await update.message.reply_text("📉 **حداقل مبلغ سبد خرید** چقدر باشد؟ (تومان)\n(اگر محدودیتی ندارد 0 بزنید)")
    return ADD_COUPON_MIN


async def get_coupon_min(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        min_order = int(update.message.text)
        limit = 1000  # پیش‌فرض ۱۰۰۰ بار مصرف
        db.add_coupon(context.user_data['c_code'], context.user_data['c_type'], context.user_data['c_val'], min_order,
                      limit)
        await update.message.reply_text("✅ کد تخفیف ساخته شد.", reply_markup=kb.admin_menu())
        return ConversationHandler.END
    except:
        await update.message.reply_text("عدد!")
        return ADD_COUPON_MIN