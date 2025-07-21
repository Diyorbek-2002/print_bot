import os
import fitz  # pip install pymupdf
from datetime import datetime, date
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

user_state = {}
user_data = {}

CARD_NUMBER = "9860 0121 0611 7372"
CARD_NAME = "Diyorbek Ziyodullayev"
ADMIN_USERNAME = "@OnlinePrintAdm"
ADMIN_CHAT_ID = 5660490669

ADDRESS = (
    "\n📍 Manzil: Toshkent, Sergeli 4\n"
    "🚘 Mo‘ljal: Avtosalon\n"
    "📞 Tel: +998 77 129 16 36\n"
    "📞 Tel: +998 93 596 12 66\n"
    "📦 Dastavka mavjud!"
)

def yoz_order_faylga(user_id, data):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    with open("orders.txt", "a", encoding="utf-8") as file:
        file.write(
            f"🕒 {now}\n"
            f"👤 Foydalanuvchi ID: {user_id}\n"
            f"📄 Betlar: {data['pages']}\n"
            f"📀 Format: {data['format'].upper()}\n"
            f"📦 Nusxa: {data['copies']}\n"
            f"💰 Narx: {data['price']} so'm\n"
            f"💳 Oldindan: {data['advance']} so'm\n"
            f"📞 Telefon: {data.get('phone', 'yo‘q')}\n"
            f"Ismi: {data.get('fullname', 'yo‘q')}\n"
            f"{'-'*30}\n"
        )

async def yubor_admin(update: Update, context: ContextTypes.DEFAULT_TYPE, data):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    username = update.effective_user.username or "username yo‘q"
    text = (
        f"📥 YANGI BUYURTMA!\n"
        f"🕒 {now}\n"
        f"👤 @{username}\n"
        f"📄 Betlar: {data.get('pages', 'kiritilmagan')}\n"
        f"📀 Format: {data.get('format', 'kiritilmagan').upper()}\n"
        f"📦 Nusxa: {data.get('copies', 'kiritilmagan')}\n"
        f"💰 Narx: {data.get('price', 'hisoblanmagan')} so'm\n"
        f"💳 Oldindan: {data.get('advance', 'hisoblanmagan')} so'm\n"
        f"📞 Telefon: {data.get('phone', 'yo‘q')}\n"
        f"Ismi: {data.get('fullname', 'yo‘q')}"
    )
    try:
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=text)
        # Agar tolov rasmi bo‘lsa, uni ham yuborish
        if 'payment_file_path' in data:
            with open(data['payment_file_path'], "rb") as file:
                await context.bot.send_document(chat_id=ADMIN_CHAT_ID, document=file)
    except:
        await update.message.reply_text("⚠️ Adminga xabar yuborilmadi.")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_state[user_id] = "awaiting_fullname"
    await update.message.reply_text("Salom! Bizni tanlaganingizdan xursandmiz 😊")
    await update.message.reply_text("Iltimos, to'liq ismingizni yuboring:")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    state = user_state.get(user_id)

    if state == "awaiting_fullname":
        user_data[user_id] = {"fullname": update.message.text}
        user_state[user_id] = "awaiting_phone"
        await update.message.reply_text("📞 Endi telefon raqamingizni yuboring:")
        return

    elif state == "awaiting_phone":
        phone = update.message.text
        if phone.startswith("+998") or phone.isdigit():
            user_data[user_id]["phone"] = phone
            user_state[user_id] = "awaiting_pdf_or_page"
            await update.message.reply_text("📘 Endi kitobni PDF fayl ko‘rinishida yuboring yoki sahifa sonini yozing:")
            await yubor_admin(update, context, user_data[user_id])
        else:
            await update.message.reply_text("To‘g‘ri raqam yuboring (masalan: +99890...)")
        return

    if update.message.document and state == "awaiting_pdf_or_page":
        file = await update.message.document.get_file()
        file_path = f"{user_id}.pdf"
        await file.download_to_drive(file_path)

        doc = fitz.open(file_path)
        page_count = doc.page_count
        doc.close()

        try:
            await context.bot.send_document(chat_id=ADMIN_CHAT_ID, document=open(file_path, "rb"))
        except:
            await update.message.reply_text("⚠️ PDF fayl adminga yuborilmadi.")

        os.remove(file_path)

        user_data[user_id]["pages"] = page_count
        user_state[user_id] = "awaiting_format"

        await update.message.reply_text(f"📄 PDF {page_count} betdan iborat.")
        await update.message.reply_text("A4 formatdami yoki A5 formatda chiqaraylikmi?")
        return

    if state == "awaiting_pdf_or_page":
        if update.message.text.isdigit():
            user_data[user_id]["pages"] = int(update.message.text)
            user_state[user_id] = "awaiting_format"
            await update.message.reply_text("A4 formatdami yoki A5 formatda chiqaraylikmi?")
        else:
            await update.message.reply_text("PDF yuboring yoki sahifa sonini yozing.")

    elif state == "awaiting_format":
        matn = update.message.text.lower()
        if "a4" in matn or "a5" in matn:
            user_data[user_id]["format"] = "a4" if "a4" in matn else "a5"
            user_state[user_id] = "awaiting_copy_count"
            await update.message.reply_text("Nechta nusxa chiqarilsin?")
        else:
            await update.message.reply_text("A4 yoki A5 deb yozing.")

    elif state == "awaiting_copy_count":
        if update.message.text.isdigit():
            nusxa = int(update.message.text)
            data = user_data[user_id]
            data["copies"] = nusxa

            if data["format"] == "a4":
                total = (data["pages"] * 200 + 15000) * nusxa
            else:
                total = round(((data["pages"] * 30000) / 200) * nusxa)

            data["price"] = total
            data["advance"] = round(total * 0.5)
            user_state[user_id] = "awaiting_payment_screenshot"

            await update.message.reply_text(
                f"📘 Nusxa soni: {nusxa} ta\n"
                f"💰 Umumiy narx: {total} so'm\n"
                f"💳 Oldindan to‘lov: {data['advance']} so'm\n"
                f"💳 Karta: {CARD_NUMBER}\n"
                f"👤 Karta egasi: {CARD_NAME}"
            )
            await update.message.reply_text(ADDRESS)
            await update.message.reply_text(f"📄 Fayllarni admin: {ADMIN_USERNAME}")
            await update.message.reply_text("✅ To‘lov chekini yuboring:")
            await yubor_admin(update, context, data)
        else:
            await update.message.reply_text("Nusxa sonini raqamda yozing.")

    elif state == "awaiting_payment_screenshot":
        if update.message.photo or update.message.document:
            # Chek faylni saqlab adminga yuborish
            if update.message.photo:
                file = await update.message.photo[-1].get_file()
            else:
                file = await update.message.document.get_file()

            file_path = f"{user_id}_payment.jpg"
            await file.download_to_drive(file_path)
            user_data[user_id]['payment_file_path'] = file_path

            user_state[user_id] = "done"
            yoz_order_faylga(user_id, user_data[user_id])
            await yubor_admin(update, context, user_data[user_id])
            await update.message.reply_text("✅ To‘lov qabul qilindi!")

            tugma = [["/start ➕ Yangi buyurtma"]]
            markup = ReplyKeyboardMarkup(tugma, one_time_keyboard=True, resize_keyboard=True)
            await update.message.reply_text("Yana buyurtma bermoqchimisiz?", reply_markup=markup)
            os.remove(file_path)
        else:
            await update.message.reply_text("To‘lov chekini rasm yoki fayl sifatida yuboring.")

async def stat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_CHAT_ID:
        await update.message.reply_text("⛔ Bu buyruq faqat admin uchun!")
        return

    total = today = 0
    bugun = date.today().isoformat()

    if os.path.exists("orders.txt"):
        with open("orders.txt", encoding="utf-8") as file:
            text = file.read()
            total = text.count("👤 Foydalanuvchi ID:")
            today = text.count(bugun)

    await update.message.reply_text(
        f"📊 Buyurtmalar statistikasi:\n"
        f"📅 Bugun: {today} ta\n"
        f"📦 Umumiy: {total} ta"
    )

if __name__ == '__main__':
    app = ApplicationBuilder().token("7752602132:AAEc-wOYaOR6eiJhcIpAzoGEwzoJKOihNpk").build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stat", stat))
    app.add_handler(MessageHandler(filters.ALL, handle_message))
    print("🤖 Bot Railway’da ishga tushdi...")
    app.run_polling()
