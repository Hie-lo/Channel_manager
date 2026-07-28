"""
هندلرهای ادمین برای مدیریت آموزش‌ها
مخصوص گرفتن file_id از ویدیوهای آپلود شده
"""

from telegram import Update
from telegram.ext import ContextTypes

from app.config import settings
from app.utils.logger import log


async def admin_get_file_id_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    وقتی ادمین یه ویدیو یا فایل به ربات بفرسته،
    file_id رو بهش برمی‌گردونه تا بتونه استفاده کنه
    """
    user = update.effective_user

    if user.id != settings.ADMIN_CHAT_ID:
        return

    message = update.message
    file_id = None
    file_type = None

    if message.video:
        file_id = message.video.file_id
        file_type = "video"
    elif message.document:
        file_id = message.document.file_id
        file_type = "document"
    elif message.photo:
        file_id = message.photo[-1].file_id
        file_type = "photo"
    elif message.animation:
        file_id = message.animation.file_id
        file_type = "animation"

    if not file_id:
        return

    await message.reply_text(
        f"📎 <b>File ID دریافت شد!</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🎯 نوع: {file_type}\n"
        f"🔑 File ID:\n"
        f"<code>{file_id}</code>\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"💡 این ID رو کپی کنید و در فایل\n"
        f"<code>app/services/tutorial_seeder.py</code>\n"
        f"استفاده کنید.\n\n"
        f"مثال:\n"
        f"<code>video_file_id=\"{file_id[:30]}...\"</code>",
        parse_mode="HTML",
    )

    log.info(f"📎 File ID برای ادمین: {file_type} - {file_id[:40]}...")