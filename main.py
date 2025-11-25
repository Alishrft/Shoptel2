import logging
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ConversationHandler, \
    filters
from config import BOT_TOKEN, ADMIN_ID
import customer_panel as cust
import admin_panel as admin
import database as db
from telegram.ext import ContextTypes
import datetime
from config import DB_NAME

# States mapping
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
ADD_VAR_NAME = 22
ADD_VAR_STOCK = 23
CNAME, PHONE, ADDRESS, POSTAL, PAY_METHOD = range(5)
SEARCH_QUERY = 30
ADD_COUPON_CODE, ADD_COUPON_VAL, ADD_COUPON_MIN = 31, 32, 33  # New states for coupon
GET_COUPON = 35

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)


async def scheduled_backup(context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_document(
        chat_id=ADMIN_ID,
        document=open(DB_NAME, 'rb'),
        caption=f"🛡 بک‌آپ خودکار دیتابیس\n📅 {datetime.datetime.now()}"
    )


if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # تنظیم جاب (Job) - هر 24 ساعت (86400 ثانیه)
    job_queue = app.job_queue
    job_queue.run_repeating(scheduled_backup, interval=86400,
                            first=10)  # اولین بک‌آپ ۱۰ ثانیه بعد از اجرا میاد برای تست


async def handle_receipt(update, context):
    uid = update.effective_user.id
    cart = db.get_cart(uid)
    if not cart:
        await update.message.reply_text("سبد خرید خالی است.")
        return

    photo = update.message.photo[-1].file_id
    caption = update.message.caption or ""

    # دریافت اطلاعات کاربر
    u = db.get_user_info(uid)
    user_det = f"{u.get('name', 'ناشناس')}\n{u.get('phone', '-')}\n{u.get('address', '-')}\n{u.get('postal', '-')}"

    # محاسبه مبالغ
    cart_total = sum([i['price'] * i['qty'] for i in cart])
    shipping = int(db.get_setting('shipping_cost', 0))

    # خواندن تخفیف از حافظه (چون کاربر قبلش وارد کرده)
    discount = context.user_data.get('discount', 0)

    # مبلغ نهایی
    final_total_int = cart_total + shipping - discount
    final_total_str = f"{final_total_int:,}"

    # آماده‌سازی لیست آیتم‌ها برای ذخیره
    items_to_save = []
    cart_txt = ""
    for i in cart:
        v_name = i.get('var_name', "")
        items_to_save.append({
            "product_id": i['product_id'],
            "variant_id": i['variant_id'],
            "name": i['name'],
            "var_name": v_name,
            "qty": i['qty'],
            "price": i['price']
        })
        cart_txt += f"▫️ {i['name']} {f'({v_name})' if v_name else ''} - {i['qty']} عدد\n"

    # ذخیره سفارش (همراه با مقدار تخفیف)
    oid = db.save_order(uid, user_det, items_to_save, final_total_str, "Card", "", "Pending Approval", photo, discount)

    # مصرف کد تخفیف (اگر استفاده شده باشد)
    if discount > 0:
        code = context.user_data.get('coupon_code')
        if code: db.use_coupon(uid, code)

    db.clear_cart(uid)

    await update.message.reply_text("✅ فیش شما دریافت شد.\nمنتظر بررسی و تایید ادمین باشید.")

    # ارسال به مدیر
    from telegram import InlineKeyboardMarkup, InlineKeyboardButton
    btn = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ تایید", callback_data=f"confirm_{oid}_{uid}"),
         InlineKeyboardButton("❌ رد", callback_data=f"reject_{oid}_{uid}")]
    ])

    admin_msg = (
        f"🧾 **فیش جدید**\n\n"
        f"👤 خریدار:\n{user_det}\n\n"
        f"🛒 سفارش:\n{cart_txt}\n"
        f"💰 کالاها: {cart_total:,}\n"
        f"🚚 پست: {shipping:,}\n"
        f"🎁 تخفیف: {discount:,}\n"
        f"💵 **مبلغ کل: {final_total_str} تومان**\n"
        f"📝 توضیحات: {caption}"
    )

    await context.bot.send_photo(ADMIN_ID, photo, caption=admin_msg, reply_markup=btn, parse_mode='Markdown')

if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # --- Admin Conversations ---

    # Add Product
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(admin.add_prod_start, pattern='^add_prod$')],
        states={
            NAME: [MessageHandler(filters.TEXT, admin.get_name)],
            DESC: [MessageHandler(filters.TEXT, admin.get_desc)],
            PRICE: [MessageHandler(filters.TEXT, admin.get_price)],
            STOCK: [MessageHandler(filters.TEXT, admin.get_stock)],
            CAT: [CallbackQueryHandler(admin.get_cat)],
            PHOTO: [MessageHandler(filters.ALL, admin.get_photo)]
        },
        fallbacks=[CommandHandler('cancel', admin.cancel)]
    ))

    # Add Category
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(admin.new_cat_start, pattern='^new_cat$')],
        states={ADD_CAT: [MessageHandler(filters.TEXT, admin.new_cat_save)]},
        fallbacks=[CommandHandler('cancel', admin.cancel)]
    ))

    # Set Card Info
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(admin.set_card_start, pattern='^set_card_info$')],
        states={CARD_INFO: [MessageHandler(filters.TEXT, admin.set_card_save)]},
        fallbacks=[CommandHandler('cancel', admin.cancel)]
    ))

    # Set Shipping Cost
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(admin.set_shipping_start, pattern='^set_ship$')],
        states={SHIPPING_PRICE: [MessageHandler(filters.TEXT, admin.set_shipping_save)]},
        fallbacks=[CommandHandler('cancel', admin.cancel)]
    ))

    # Set Channel ID
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(admin.set_channel_start, pattern='^set_channel_id$')],
        states={SET_CHANNEL: [MessageHandler(filters.TEXT, admin.set_channel_save)]},
        fallbacks=[CommandHandler('cancel', admin.cancel)]
    ))

    # Set Merchant ID
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(admin.set_merchant_start, pattern='^set_merchant$')],
        states={SET_MERCHANT: [MessageHandler(filters.TEXT, admin.set_merchant_save)]},
        fallbacks=[CommandHandler('cancel', admin.cancel)]
    ))

    # Set Support Text
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(admin.set_support_text_start, pattern='^set_support_text$')],
        states={SET_SUPPORT_TEXT: [MessageHandler(filters.TEXT, admin.set_support_text_save)]},
        fallbacks=[CommandHandler('cancel', admin.cancel)]
    ))

    # Send Message to User
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(admin.send_msg_start, pattern='^msg_user_')],
        states={SEND_USER_MSG: [MessageHandler(filters.TEXT, admin.send_msg_send)]},
        fallbacks=[CommandHandler('cancel', admin.cancel)]
    ))

    # Send Tracking Code
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(admin.send_track_start, pattern='^track_user_')],
        states={SEND_USER_TRACK: [MessageHandler(filters.TEXT, admin.send_track_send)]},
        fallbacks=[CommandHandler('cancel', admin.cancel)]
    ))

    # Edit Product Value
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(admin.edit_prod_val_start, pattern='^ed_(name|price|stock|del|img)_')],
        states={
            EDIT_VAL: [MessageHandler(filters.TEXT, admin.edit_prod_val_save)],
            EDIT_PROD_IMG: [MessageHandler(filters.PHOTO, admin.edit_prod_img_save)]
        },
        fallbacks=[CommandHandler('cancel', admin.cancel)]
    ))

    # Edit Category Name
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(admin.edit_cat_action, pattern='^edcatren_')],
        states={EDIT_CAT_NAME: [MessageHandler(filters.TEXT, admin.edit_cat_save)]},
        fallbacks=[CommandHandler('cancel', admin.cancel)]
    ))

    # Add Variant
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(admin.add_var_start, pattern='^add_var$')],
        states={
            ADD_VAR_NAME: [MessageHandler(filters.TEXT, admin.get_var_name)],
            ADD_VAR_STOCK: [MessageHandler(filters.TEXT, admin.get_var_stock)]
        },
        fallbacks=[CommandHandler('cancel', admin.cancel)]
    ))

    # Broadcast Message
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(admin.broadcast_start, pattern='^broadcast$')],
        states={BROADCAST_MSG: [MessageHandler(filters.ALL & ~filters.COMMAND, admin.broadcast_send)]},
        fallbacks=[CommandHandler('cancel', admin.cancel)]
    ))

    # Add Coupon
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(admin.add_coupon_start, pattern='^add_coupon$')],
        states={
            admin.ADD_COUPON_CODE: [MessageHandler(filters.TEXT, admin.get_coupon_code)],
            admin.ADD_COUPON_VAL: [MessageHandler(filters.TEXT, admin.get_coupon_val)],
            admin.ADD_COUPON_MIN: [MessageHandler(filters.TEXT, admin.get_coupon_min)]
        },
        fallbacks=[CommandHandler('cancel', admin.cancel)]
    ))

    # -----------------------
    # Customer Checkout Flow
    # -----------------------
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(cust.start_checkout, pattern='^checkout$')],
        states={
            # Handling POSTAL step which can receive button click or text
            POSTAL: [
                CallbackQueryHandler(cust.get_postal, pattern='^yes$'),
                CallbackQueryHandler(cust.get_new, pattern='^no$'),
                MessageHandler(filters.TEXT, cust.get_postal)
            ],
            CNAME: [MessageHandler(filters.TEXT, cust.get_name)],
            PHONE: [MessageHandler(filters.TEXT, cust.get_phone)],
            ADDRESS: [MessageHandler(filters.TEXT, cust.get_address)],

            # Payment method selection and Coupon handling
            PAY_METHOD: [
                CallbackQueryHandler(cust.process_pay, pattern='^(card|online|cart_back)$'),
                CallbackQueryHandler(cust.apply_coupon, pattern='^ask_coupon$'),
                CallbackQueryHandler(cust.process_pay, pattern='^back_to_pay$')
            ],

            # Entering Coupon Code
            GET_COUPON: [MessageHandler(filters.TEXT, cust.check_coupon)]
        },
        fallbacks=[CommandHandler('cancel', admin.cancel)]
    ))

    # Customer Search
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(cust.search_start, pattern='^search_mode$')],
        states={SEARCH_QUERY: [MessageHandler(filters.TEXT, cust.perform_search)]},
        fallbacks=[CommandHandler('cancel', admin.cancel)]
    ))
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(admin.add_coupon_start, pattern='^add_coupon$')],
        states={
            admin.ADD_COUPON_CODE: [MessageHandler(filters.TEXT, admin.get_coupon_code)],
            admin.ADD_COUPON_VAL: [MessageHandler(filters.TEXT, admin.get_coupon_val)],
            admin.ADD_COUPON_MIN: [MessageHandler(filters.TEXT, admin.get_coupon_min)]
        },
        fallbacks=[CommandHandler('cancel', admin.cancel)]
    ))
    # --- General Handlers ---
    app.add_handler(CommandHandler('start', cust.start))
    app.add_handler(CallbackQueryHandler(cust.start, pattern='^start$'))

    app.add_handler(CallbackQueryHandler(cust.view_cats, pattern='^cats$'))
    app.add_handler(CallbackQueryHandler(cust.view_products, pattern='^cat_'))

    app.add_handler(CallbackQueryHandler(cust.pre_add_cart, pattern='^preadd_'))
    app.add_handler(CallbackQueryHandler(cust.add_variant_cart, pattern='^addvar_'))

    app.add_handler(CallbackQueryHandler(cust.toggle_like, pattern='^like_'))
    app.add_handler(CallbackQueryHandler(cust.view_wishlist, pattern='^wishlist$'))

    app.add_handler(CallbackQueryHandler(cust.add_cart, pattern='^add_'))
    app.add_handler(CallbackQueryHandler(cust.view_cart, pattern='^cart$'))
    app.add_handler(CallbackQueryHandler(cust.clear_cart_handler, pattern='^clear_cart$'))
    app.add_handler(CallbackQueryHandler(cust.modify_cart, pattern='^(inc|dec|del)_'))

    app.add_handler(CallbackQueryHandler(cust.history, pattern='^history$'))
    app.add_handler(CallbackQueryHandler(cust.support, pattern='^support$'))
    app.add_handler(CallbackQueryHandler(cust.check_zp, pattern='^check_zp$'))
    app.add_handler(CallbackQueryHandler(cust.sort_results, pattern='^sort_'))
    app.add_handler(CallbackQueryHandler(admin.download_excel, pattern='^download_excel$'))
    app.add_handler(CallbackQueryHandler(admin.manage_coupons, pattern='^manage_coupons$'))
    app.add_handler(CallbackQueryHandler(admin.delete_coupon, pattern='^del_coup_'))
    # WebApp Data Handler
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, cust.handle_webapp_data))

    # --- Admin General Handlers ---
    app.add_handler(CallbackQueryHandler(admin.admin_dashboard, pattern='^admin_menu$'))
    app.add_handler(CallbackQueryHandler(admin.send_reports, pattern='^admin_reports$'))
    app.add_handler(CallbackQueryHandler(admin.manage_settings, pattern='^settings$'))
    app.add_handler(CallbackQueryHandler(admin.toggle_payment, pattern='^set_pay$'))
    app.add_handler(CallbackQueryHandler(admin.toggle_lock, pattern='^set_lock$'))

    app.add_handler(CallbackQueryHandler(admin.manage_products, pattern='^mng_prods$'))
    app.add_handler(CallbackQueryHandler(admin.manage_cats, pattern='^mng_cats$'))
    app.add_handler(CallbackQueryHandler(admin.manage_variants, pattern='^mng_var_'))
    app.add_handler(CallbackQueryHandler(admin.delete_variant, pattern='^delvar_'))

    app.add_handler(CallbackQueryHandler(admin.user_list, pattern='^users_list$'))
    app.add_handler(CallbackQueryHandler(admin.manage_single_user, pattern='^manage_user_'))

    app.add_handler(CallbackQueryHandler(admin.edit_prod_list, pattern='^edit_prod_list$'))
    app.add_handler(CallbackQueryHandler(admin.edit_prod_select, pattern='^edit_p_'))

    app.add_handler(CallbackQueryHandler(admin.edit_cat_list, pattern='^edit_cat_list$'))
    app.add_handler(CallbackQueryHandler(admin.edit_cat_select, pattern='^edcat_'))
    app.add_handler(
        CallbackQueryHandler(admin.edit_cat_action, pattern='^edcatdel_'))  # Rename is handled in conv above

    app.add_handler(CallbackQueryHandler(admin.handle_receipt_decision, pattern='^(confirm|reject)_'))

    # Receipt Handler (Must be last)
    app.add_handler(MessageHandler(filters.PHOTO, handle_receipt))

    print("✅ Bot is Running Successfully!")

    app.run_polling()
