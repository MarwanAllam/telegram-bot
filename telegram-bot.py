from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

# هنا تحط التوكن بتاعك
TOKEN = "8427063575:AAGyQSTbjGHOrBHhZeVucVnNWc47amwR7RA"

queues = {}
awaiting_input = {}  # لتخزين المرحلة الحالية من الأسئلة لكل شات


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

    if chat_id in queues and queues[chat_id].get("members") is not None and not queues[chat_id].get("closed", True):
        await update.message.reply_text("⚠️ فيه دور شغال بالفعل، اقفله الأول قبل تبدأ جديد.")
        return

    awaiting_input[chat_id] = {"step": "teacher"}
    await update.message.reply_text("👩‍🏫 اكتب اسم المعلمة:")


async def collect_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ✅ تجاهل أي تحديث مفيهوش رسالة نصية
    if not update.message or not update.message.text:
        return

    chat_id = update.effective_chat.id
    user_input = update.message.text.strip()

    if chat_id not in awaiting_input:
        return

    step = awaiting_input[chat_id]["step"]

    if step == "teacher":
        awaiting_input[chat_id]["teacher"] = user_input
        awaiting_input[chat_id]["step"] = "class_name"
        await update.message.reply_text("📘 اكتب اسم الحلقة:")
        return

    elif step == "class_name":
        teacher_name = awaiting_input[chat_id]["teacher"]
        class_name = user_input
        creator_name = update.effective_user.full_name  # 👤 اسم اللي بدأ الدور

        # إنشاء الدور
        queues[chat_id] = {
            "creator": update.effective_user.id,
            "creator_name": creator_name,
            "admins": set(),
            "members": [],
            "removed": set(),
            "all_joined": set(),
            "closed": False,
            "usernames": {},
            "teacher_name": teacher_name,
            "class_name": class_name
        }

        del awaiting_input[chat_id]

        text = (
            f"👤 *بدأ الدور:* {creator_name}\n"
            f"📚 *اسم المعلمة:* {teacher_name}\n"
            f"🏫 *اسم الحلقة:* {class_name}\n\n"
            f"🎯 *القائمة الحالية:* (فاضية)"
        )

        await update.message.reply_text(text, reply_markup=make_main_keyboard(chat_id), parse_mode="Markdown")


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

        q["usernames"][user.id] = user.full_name

        if user.id in q["removed"]:
            await query.answer("🚫 تم حذفك من الدور. استنى الدور الجديد.")
            return

        if user.id in q["members"]:
            q["members"].remove(user.id)
            if user.id in q["all_joined"]:
                q["all_joined"].remove(user.id)
            await query.answer("❌ تم انسحابك.")
        else:
            q["members"].append(user.id)
            q["all_joined"].add(user.id)
            await query.answer("✅ تم تسجيلك!")

        members_text = "\n".join(
            [f"{i+1}. {q['usernames'].get(uid, 'مجهول')}" for i, uid in enumerate(q["members"])]
        ) or "(فاضية)"
        text = (
            f"👤 *بدأ الدور:* {q['creator_name']}\n"
            f"📚 *اسم المعلمة:* {q['teacher_name']}\n"
            f"🏫 *اسم الحلقة:* {q['class_name']}\n\n"
            f"🎯 *القائمة الحالية:*\n{members_text}"
        )
        await query.edit_message_text(text, reply_markup=make_main_keyboard(chat_id), parse_mode="Markdown")

    elif action == "remove_menu":
        if not is_admin_or_creator(user.id, q):
            await query.answer("🚫 مش من صلاحياتك.")
            return
        if not q["members"]:
            await query.answer("📋 مفيش حد في الدور.")
            return

        keyboard = []
        for i, uid in enumerate(q["members"]):
            name = q["usernames"].get(uid, "مجهول")
            keyboard.append([InlineKeyboardButton(f"❌ {name}", callback_data=f"remove_member|{chat_id}|{i}")])
        keyboard.append([InlineKeyboardButton("🔙 إلغاء", callback_data=f"cancel_remove|{chat_id}")])

        await query.edit_message_text("🗑️ *اختر الاسم اللي عايز تمسحه:*",
                                      reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif action == "remove_member":
        if not is_admin_or_creator(user.id, q):
            await query.answer("🚫 مش من صلاحياتك.")
            return
        index = int(parts[2])
        if 0 <= index < len(q["members"]):
            target = q["members"].pop(index)
            q["removed"].add(target)

        members_text = "\n".join(
            [f"{i+1}. {q['usernames'].get(uid, 'مجهول')}" for i, uid in enumerate(q["members"])]
        ) or "(فاضية)"
        text = (
            f"👤 *بدأ الدور:* {q['creator_name']}\n"
            f"📚 *اسم المعلمة:* {q['teacher_name']}\n"
            f"🏫 *اسم الحلقة:* {q['class_name']}\n\n"
            f"🎯 *القائمة الحالية:*\n{members_text}"
        )
        await query.edit_message_text(text, reply_markup=make_main_keyboard(chat_id), parse_mode="Markdown")

    elif action == "cancel_remove":
        members_text = "\n".join(
            [f"{i+1}. {q['usernames'].get(uid, 'مجهول')}" for i, uid in enumerate(q["members"])]
        ) or "(فاضية)"
        text = (
            f"👤 *بدأ الدور:* {q['creator_name']}\n"
            f"📚 *اسم المعلمة:* {q['teacher_name']}\n"
            f"🏫 *اسم الحلقة:* {q['class_name']}\n\n"
            f"🎯 *القائمة الحالية:*\n{members_text}"
        )
        await query.edit_message_text(text, reply_markup=make_main_keyboard(chat_id), parse_mode="Markdown")
        await query.answer("تم الإلغاء ✅")

    elif action == "close":
        if not is_admin_or_creator(user.id, q):
            await query.answer("🚫 مش من صلاحياتك.")
            return

        if not q["members"]:
            await query.answer("📋 مفيش حد في الدور يقفل عليه.")
            return

        q["closed"] = True
        await query.edit_message_text("🔒 تم قفل الدور.\nالتسجيل متوقف ✅")


# ✅ أمر /forceclose لأي مستخدم
async def force_close(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id in queues:
        del queues[chat_id]
    if chat_id in awaiting_input:
        del awaiting_input[chat_id]
    await update.message.reply_text("🧹 تم مسح أي جلسة قديمة أو دور شغال ✅")


app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("forceclose", force_close))
app.add_handler(CallbackQueryHandler(button))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, collect_info))

print("🤖 البوت شغال...")
app.run_polling()
