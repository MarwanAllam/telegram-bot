from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# هنا تحط التوكن بتاعك
TOKEN = "8427063575:AAGyQSTbjGHOrBHhZeVucVnNWc47amwR7RA"

# بنخزن حالة كل جروب
queues = {}

def make_main_keyboard(chat_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📝 انضم / انسحب", callback_data=f"join|{chat_id}")
        ],
        [
            InlineKeyboardButton("🗑️ ريموف", callback_data=f"remove_menu|{chat_id}"),
            InlineKeyboardButton("🔒 إنهاء الدور", callback_data=f"close|{chat_id}")
        ]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user

    # ✅ منع تشغيل /start جديد لو الدور الحالي مفتوح
    q = queues.get(chat_id)
    if q and not q["closed"]:
        await update.message.reply_text(
            "⚠️ فيه دور شغال بالفعل. استخدم /forceclose لو عايز تقفله وتبدأ جديد."
        )
        return

    # إنشاء الدور الجديد
    queues[chat_id] = {
        "creator": user.id,
        "members": [],
        "removed": set(),
        "all_joined": set(),
        "closed": False
    }

    text = f"🎯 الدور بدأ بواسطة {user.full_name}\n\n*القائمة الحالية:* (فاضية)"
    await update.message.reply_text(
        text,
        reply_markup=make_main_keyboard(chat_id),
        parse_mode="Markdown"
    )

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

    # 🧩 انضم / انسحب
    if action == "join":
        if q["closed"]:
            await query.answer("🚫 التسجيل مقفول.")
            return
        name = user.full_name

        if name in q["removed"]:
            await query.answer("🚫 تم حذفك من الدور. استنى الدور الجديد.")
            return

        if name in q["members"]:
            q["members"].remove(name)
            if name in q["all_joined"]:
                q["all_joined"].remove(name)
            await query.answer("❌ تم انسحابك.")
        else:
            q["members"].append(name)
            q["all_joined"].add(name)
            await query.answer("✅ تم تسجيلك!")

        members_text = "\n".join([f"{i+1}. {n}" for i, n in enumerate(q["members"])]) or "(فاضية)"
        text = f"🎯 الدور شغال\n\n*القائمة الحالية:*\n{members_text}"
        await query.edit_message_text(text, reply_markup=make_main_keyboard(chat_id), parse_mode="Markdown")

    # 🗑️ فتح قايمة الريموف
    elif action == "remove_menu":
        if user.id != q["creator"]:
            await query.answer("🚫 بس اللي بدأ الدور يقدر يحذف.")
            return

        if not q["members"]:
            await query.answer("📋 مفيش حد في الدور.")
            return

        keyboard = []
        for i, n in enumerate(q["members"]):
            keyboard.append([InlineKeyboardButton(f"❌ {n}", callback_data=f"remove_member|{chat_id}|{i}")])
        keyboard.append([InlineKeyboardButton("🔙 إلغاء", callback_data=f"cancel_remove|{chat_id}")])

        text = "🗑️ *اختر الاسم اللي عايز تمسحه:*"
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    # ❌ حذف اسم
    elif action == "remove_member":
        if user.id != q["creator"]:
            await query.answer("🚫 مش من صلاحياتك.")
            return
        index = int(parts[2])
        if 0 <= index < len(q["members"]):
            target = q["members"].pop(index)
            q["removed"].add(target)

        members_text = "\n".join([f"{i+1}. {n}" for i, n in enumerate(q["members"])]) or "(فاضية)"
        text = f"🎯 الدور شغال\n\n*القائمة الحالية:*\n{members_text}"
        await query.edit_message_text(text, reply_markup=make_main_keyboard(chat_id), parse_mode="Markdown")
        await query.answer(f"❌ تم حذف {target}")

    # 🔙 إلغاء قائمة الريموف
    elif action == "cancel_remove":
        members_text = "\n".join([f"{i+1}. {n}" for i, n in enumerate(q["members"])]) or "(فاضية)"
        text = f"🎯 الدور شغال\n\n*القائمة الحالية:*\n{members_text}"
        await query.edit_message_text(text, reply_markup=make_main_keyboard(chat_id), parse_mode="Markdown")
        await query.answer("تم الإلغاء ✅")

    # 🔒 قفل الدور
    elif action == "close":
        if user.id != q["creator"]:
            await query.answer("🚫 بس اللي بدأ الدور يقدر يقفله.")
            return
        q["closed"] = True

        text = "🔒 تم قفل الدور.\nالتسجيل متوقف ✅"
        await query.edit_message_text(text)
        await query.answer("تم القفل.")

        all_joined = list(q["all_joined"])
        removed = list(q["removed"])
        remaining = [n for n in q["members"] if n not in removed]

        full_list_text = "\n".join([f"{i+1}. {n}" for i, n in enumerate(all_joined)]) or "(فاضية)"
        removed_text = "\n".join([f"{i+1}. {n}" for i, n in enumerate(removed)]) or "(مفيش)"
        remaining_text = "\n".join([f"{i+1}. {n}" for i, n in enumerate(remaining)]) or "(مفيش)"

        final_text = (
            "📋 *القائمة النهائية للدور:*\n\n"
            "👥 *كل اللي سجلوا فعلاً (اللي كانوا جزء من الدور):*\n"
            f"{full_list_text}\n\n"
            "✅ *تمت القراءه:*\n"
            f"{removed_text}\n\n"
            "❌ *لم يقرأ:*\n"
            f"{remaining_text}"
        )

        await query.message.reply_text(final_text, parse_mode="Markdown")

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("forceclose", force_close))
app.add_handler(CallbackQueryHandler(button))

print("🤖 البوت شغال...")
app.run_polling()
