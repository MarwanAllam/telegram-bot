from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# هنا تحط التوكن بتاعك
TOKEN = "8427063575:AAGyQSTbjGHOrBHhZeVucVnNWc47amwR7RA"


queues = {}

def make_main_keyboard(chat_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 انضم / انسحب", callback_data=f"join|{chat_id}")],
        [
            InlineKeyboardButton("🗑️ ريموف", callback_data=f"remove_menu|{chat_id}"),
            InlineKeyboardButton("🔒 إنهاء الدور", callback_data=f"close|{chat_id}")
        ],
        [InlineKeyboardButton("⭐ إدارة المشرفين", callback_data=f"manage_admins|{chat_id}")]
    ])

def is_admin_or_creator(user_id, q):
    return user_id == q["creator"] or user_id in q["admins"]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user

    q = queues.get(chat_id)
    if q and not q["closed"]:
        await update.message.reply_text("⚠️ فيه دور شغال بالفعل. اقفله الأول أو استخدم /forceclose.")
        return

    queues[chat_id] = {
        "creator": user.id,
        "admins": set(),
        "members": [],
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
        await update.message.reply_text("❌ مفيش دور شغال.")
        return

    if user.id != q["creator"]:
        await update.message.reply_text("🚫 بس اللي بدأ الدور يقدر يقفله.")
        return

    del queues[chat_id]
    await update.message.reply_text("✅ تم إنهاء الجلسة الحالية.")

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
        name = user.full_name

        if name in q["removed"]:
            await query.answer("🚫 تم حذفك من الدور. استنى الدور الجديد.")
            return

        if name in q["members"]:
            q["members"].remove(name)
            q["all_joined"].discard(name)
            await query.answer("❌ تم انسحابك.")
        else:
            q["members"].append(name)
            q["all_joined"].add(name)
            await query.answer("✅ تم تسجيلك!")

        members_text = "\n".join([f"{i+1}. {n}" for i, n in enumerate(q["members"])]) or "(فاضية)"
        text = f"🎯 الدور شغال\n\n*القائمة الحالية:*\n{members_text}"
        await query.edit_message_text(text, reply_markup=make_main_keyboard(chat_id), parse_mode="Markdown")

    elif action == "remove_menu":
        if not is_admin_or_creator(user.id, q):
            await query.answer("🚫 مش من صلاحياتك.")
            return
        if not q["members"]:
            await query.answer("📋 مفيش حد في الدور.")
            return

        keyboard = []
        for i, n in enumerate(q["members"]):
            keyboard.append([InlineKeyboardButton(f"❌ {n}", callback_data=f"remove_member|{chat_id}|{i}")])
        keyboard.append([InlineKeyboardButton("🔙 إلغاء", callback_data=f"cancel_remove|{chat_id}")])

        await query.edit_message_text("🗑️ *اختر الاسم اللي عايز تمسحه:*",
                                      reply_markup=InlineKeyboardMarkup(keyboard),
                                      parse_mode="Markdown")

    elif action == "remove_member":
        if not is_admin_or_creator(user.id, q):
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

    elif action == "cancel_remove":
        members_text = "\n".join([f"{i+1}. {n}" for i, n in enumerate(q["members"])]) or "(فاضية)"
        text = f"🎯 الدور شغال\n\n*القائمة الحالية:*\n{members_text}"
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

        all_joined = list(q["all_joined"])
        removed = list(q["removed"])
        remaining = [n for n in q["members"] if n not in removed]

        full_list_text = "\n".join([f"{i+1}. {n}" for i, n in enumerate(all_joined)]) or "(فاضية)"
        removed_text = "\n".join([f"{i+1}. {n}" for i, n in enumerate(removed)]) or "(مفيش)"
        remaining_text = "\n".join([f"{i+1}. {n}" for i, n in enumerate(remaining)]) or "(مفيش)"

        final_text = (
            "📋 *القائمة النهائية للدور:*\n\n"
            "👥 *كل اللي شاركوا فعليًا:*\n"
            f"{full_list_text}\n\n"
            "✅ *تمت القراءه:*\n"
            f"{removed_text}\n\n"
            "❌ *لم يقرأ:*\n"
            f"{remaining_text}"
        )
        await query.message.reply_text(final_text, parse_mode="Markdown")

    elif action == "manage_admins":
        if user.id != q["creator"]:
            await query.answer("🚫 بس اللي بدأ الدور يقدر يدير المشرفين.")
            return
        if not q["members"]:
            await query.answer("📋 مفيش حد في الدور.")
            return

        keyboard = []
        for n in q["members"]:
            label = f"⭐ أزل {n} من المشرفين" if n in q["admins"] else f"⭐ عيّن {n} مشرف"
            keyboard.append([InlineKeyboardButton(label, callback_data=f"toggle_admin|{chat_id}|{n}")])
        keyboard.append([InlineKeyboardButton("🔙 إلغاء", callback_data=f"cancel_remove|{chat_id}")])

        await query.edit_message_text("👮 *إدارة المشرفين:*",
                                      reply_markup=InlineKeyboardMarkup(keyboard),
                                      parse_mode="Markdown")

    elif action == "toggle_admin":
        if user.id != q["creator"]:
            await query.answer("🚫 بس اللي بدأ الدور يقدر يعمل كده.")
            return
        target_name = parts[2]
        if target_name in q["admins"]:
            q["admins"].remove(target_name)
        else:
            q["admins"].add(target_name)
        await query.answer("✅ تم تحديث المشرفين.")
        members_text = "\n".join([f"{i+1}. {n}{' 👮' if n in q['admins'] else ''}" for i, n in enumerate(q["members"])]) or "(فاضية)"
        text = f"🎯 الدور شغال\n\n*القائمة الحالية:*\n{members_text}"
        await query.edit_message_text(text, reply_markup=make_main_keyboard(chat_id), parse_mode="Markdown")

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("forceclose", force_close))
app.add_handler(CallbackQueryHandler(button))

print("🤖 البوت شغال...")
app.run_polling()
