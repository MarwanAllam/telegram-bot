from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# هنا تحط التوكن بتاعك
TOKEN = "8427063575:AAGyQSTbjGHOrBHhZeVucVnNWc47amwR7RA"


queues = {}

def make_main_keyboard(chat_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📝 انضم / انسحب", callback_data=f"join|{chat_id}")
        ],
        [
            InlineKeyboardButton("🗑️ ريموف", callback_data=f"remove_menu|{chat_id}"),
            InlineKeyboardButton("🔒 إنهاء الدور", callback_data=f"close|{chat_id}")
        ],
        [
            InlineKeyboardButton("⭐ إدارة المشرفين", callback_data=f"manage_admins|{chat_id}")
        ]
    ])

def is_admin_or_creator(user_id, q):
    return user_id == q["creator"] or user_id in q["admins"]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user

    q = queues.get(chat_id)
    if q and not q["closed"]:
        await update.message.reply_text("⚠️ فيه دور شغال بالفعل. استخدم /forceclose لو عايز تبدأ جديد.")
        return

    queues[chat_id] = {
        "creator": user.id,
        "admins": set(),
        "members": [],  # [{id, name}]
        "removed": set(),
        "all_joined": set(),
        "closed": False
    }

    text = f"🎯 الدور بدأ بواسطة {user.full_name}\n\n*القائمة الحالية:* (فاضية)"
    await update.message.reply_text(text, reply_markup=make_main_keyboard(chat_id), parse_mode="Markdown")

async def force_close(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user

    q = queues.get(chat_id)
    if not q:
        await update.message.reply_text("❌ مفيش دور شغال دلوقتي.")
        return

    if user.id != q["creator"]:
        await update.message.reply_text("🚫 بس اللي بدأ الدور يقدر يقفله.")
        return

    del queues[chat_id]
    await update.message.reply_text("✅ تم إنهاء الدور والجلسة السابقة اتقفلت.")

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user = query.from_user
    parts = data.split("|")
    action = parts[0]
    chat_id = int(parts[1])
    q = queues.get(chat_id)

    if not q:
        await query.answer("❌ مفيش دور شغال.")
        return

    if action == "join":
        if q["closed"]:
            await query.answer("🚫 التسجيل مقفول.")
            return

        # هل العضو موجود؟
        member = next((m for m in q["members"] if m["id"] == user.id), None)
        if member:
            q["members"].remove(member)
            q["all_joined"].discard(user.full_name)
            await query.answer("❌ تم انسحابك.")
        else:
            q["members"].append({"id": user.id, "name": user.full_name})
            q["all_joined"].add(user.full_name)
            await query.answer("✅ تم تسجيلك!")

        members_text = "\n".join([f"{i+1}. {m['name']}" for i, m in enumerate(q["members"])]) or "(فاضية)"
        admins_list = ", ".join(
            [m["name"] for m in q["members"] if m["id"] in q["admins"]]
        ) or "مفيش مشرفين"

        text = f"🎯 الدور شغال\n\n*القائمة الحالية:*\n{members_text}\n\n👮 *المشرفين:* {admins_list}"
        await query.edit_message_text(text, reply_markup=make_main_keyboard(chat_id), parse_mode="Markdown")

    elif action == "remove_menu":
        if not is_admin_or_creator(user.id, q):
            await query.answer("🚫 مش من صلاحياتك.")
            return
        if not q["members"]:
            await query.answer("📋 مفيش حد في الدور.")
            return

        keyboard = []
        for i, m in enumerate(q["members"]):
            keyboard.append([InlineKeyboardButton(f"❌ {m['name']}", callback_data=f"remove_member|{chat_id}|{i}")])
        keyboard.append([InlineKeyboardButton("🔙 إلغاء", callback_data=f"cancel_remove|{chat_id}")])

        text = "🗑️ *اختر الاسم اللي عايز تمسحه:*"
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif action == "remove_member":
        if not is_admin_or_creator(user.id, q):
            await query.answer("🚫 مش من صلاحياتك.")
            return
        index = int(parts[2])
        if 0 <= index < len(q["members"]):
            target = q["members"].pop(index)
            q["removed"].add(target["name"])

        members_text = "\n".join([f"{i+1}. {m['name']}" for i, m in enumerate(q["members"])]) or "(فاضية)"
        admins_list = ", ".join(
            [m["name"] for m in q["members"] if m["id"] in q["admins"]]
        ) or "مفيش مشرفين"

        text = f"🎯 الدور شغال\n\n*القائمة الحالية:*\n{members_text}\n\n👮 *المشرفين:* {admins_list}"
        await query.edit_message_text(text, reply_markup=make_main_keyboard(chat_id), parse_mode="Markdown")
        await query.answer(f"❌ تم حذف {target['name']}")

    elif action == "cancel_remove":
        members_text = "\n".join([f"{i+1}. {m['name']}" for i, m in enumerate(q["members"])]) or "(فاضية)"
        admins_list = ", ".join(
            [m["name"] for m in q["members"] if m["id"] in q["admins"]]
        ) or "مفيش مشرفين"
        text = f"🎯 الدور شغال\n\n*القائمة الحالية:*\n{members_text}\n\n👮 *المشرفين:* {admins_list}"
        await query.edit_message_text(text, reply_markup=make_main_keyboard(chat_id), parse_mode="Markdown")
        await query.answer("تم الإلغاء ✅")

    elif action == "close":
        if not is_admin_or_creator(user.id, q):
            await query.answer("🚫 مش من صلاحياتك.")
            return
        q["closed"] = True
        text = "🔒 تم قفل الدور.\nالتسجيل متوقف ✅"
        await query.edit_message_text(text)
        await query.answer("تم القفل.")

    elif action == "manage_admins":
        if user.id != q["creator"]:
            await query.answer("🚫 بس اللي بدأ الدور يقدر يدير المشرفين.")
            return

        if not q["members"]:
            await query.answer("📋 مفيش حد في الدور.")
            return

        keyboard = []
        for m in q["members"]:
            label = f"❌ أزل {m['name']} من المشرفين" if m["id"] in q["admins"] else f"⭐ عيّن {m['name']} مشرف"
            keyboard.append([InlineKeyboardButton(label, callback_data=f"toggle_admin|{chat_id}|{m['id']}|{m['name']}")])
        keyboard.append([InlineKeyboardButton("🔙 إلغاء", callback_data=f"cancel_remove|{chat_id}")])

        text = "👮 *إدارة المشرفين:*"
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif action == "toggle_admin":
        if user.id != q["creator"]:
            await query.answer("🚫 بس اللي بدأ الدور يقدر يعمل كده.")
            return

        target_id = int(parts[2])
        target_name = parts[3]

        if target_id in q["admins"]:
            q["admins"].remove(target_id)
            await query.answer(f"❌ تم إزالة {target_name} من المشرفين.")
        else:
            q["admins"].add(target_id)
            await query.answer(f"✅ تم تعيين {target_name} كمشرف.")
        await query.message.reply_text("✅ تم تحديث صلاحيات المشرفين.")

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("forceclose", force_close))
app.add_handler(CallbackQueryHandler(button))

print("🤖 البوت شغال...")
app.run_polling()
