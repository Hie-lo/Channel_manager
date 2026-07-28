"""
هندلرهای بخش آموزش
"""

from telegram import Update
from telegram.ext import ContextTypes

from app.database.connection import AsyncSessionLocal
from app.services.tutorial_service import (
    get_tutorial_by_key,
    get_tutorials_by_category,
)
from app.bot.keyboards.tutorial import (
    CATEGORIES,
    get_tutorial_main_menu,
    get_category_tutorials_keyboard,
    get_tutorial_back_keyboard,
)
from app.utils.logger import log


async def tutorial_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """منوی اصلی آموزش‌ها"""

    text = (
        f"📚 <b>آموزش و راهنما</b>\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"دسته مورد نظر رو انتخاب کنید:\n\n"
        f"💡 <i>در هر مرحله از ربات، دکمه ❓ راهنما\n"
        f"کنار دکمه‌ها موجوده که راهنمای اون مرحله رو\n"
        f"نمایش میده.</i>"
    )

    await update.message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=get_tutorial_main_menu(),
    )


async def tut_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """برگشت به منوی اصلی آموزش"""
    query = update.callback_query
    await query.answer()

    text = (
        f"📚 <b>آموزش و راهنما</b>\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"دسته مورد نظر رو انتخاب کنید:"
    )

    await query.edit_message_text(
        text,
        parse_mode="HTML",
        reply_markup=get_tutorial_main_menu(),
    )


async def tut_category_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """نمایش لیست آموزش‌های یک دسته"""
    query = update.callback_query
    await query.answer()

    category = query.data.replace("tut_cat_", "")

    async with AsyncSessionLocal() as session:
        tutorials = await get_tutorials_by_category(session, category)

    category_name = CATEGORIES.get(category, category)

    if not tutorials:
        await query.edit_message_text(
            f"{category_name}\n"
            f"━━━━━━━━━━━━━━━\n\n"
            f"❌ هنوز آموزشی در این دسته موجود نیست.",
            reply_markup=get_tutorial_main_menu(),
        )
        return

    text = (
        f"{category_name}\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"📄 تعداد آموزش‌ها: {len(tutorials)}\n\n"
        f"روی آموزش کلیک کنید:"
    )

    await query.edit_message_text(
        text,
        reply_markup=get_category_tutorials_keyboard(tutorials),
    )


async def tut_view_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """نمایش یک آموزش (متن یا ویدیو)"""
    query = update.callback_query
    await query.answer()

    tutorial_key = query.data.replace("tut_view_", "")

    async with AsyncSessionLocal() as session:
        tutorial = await get_tutorial_by_key(session, tutorial_key)

    if not tutorial:
        await query.edit_message_text(
            "❌ آموزش پیدا نشد!",
            reply_markup=get_tutorial_main_menu(),
        )
        return

    # اگر ویدیو داره
    if tutorial.content_type == "video" and tutorial.video_file_id:
        video_id = tutorial.video_file_id.strip()

        # چک کن file_id درسته (نه URL)
        if video_id.startswith("http://") or video_id.startswith("https://"):
            log.error(f"video_file_id URL هست، باید file_id باشه: {video_id}")
            await query.edit_message_text(
                f"⚠️ خطا در تنظیمات ویدیو.\n\n"
                f"در حال حاضر متن راهنما نمایش داده می‌شه:\n\n"
                f"{tutorial.text_content or tutorial.title}",
                parse_mode="HTML",
                reply_markup=get_tutorial_back_keyboard(tutorial.category),
            )
            return

        try:
            await context.bot.send_video(
                chat_id=query.from_user.id,
                video=video_id,
                caption=tutorial.video_caption or tutorial.title,
                parse_mode="HTML",
            )
            await query.answer("✅ ویدیو ارسال شد", show_alert=False)

            await query.edit_message_text(
                f"✅ ویدیو ارسال شد.\n\n"
                f"می‌تونید به آموزش‌های دیگه برید:",
                reply_markup=get_tutorial_back_keyboard(tutorial.category),
            )
            return
        except Exception as e:
            log.error(f"خطا در ارسال ویدیو: {e}")
            await query.edit_message_text(
                f"❌ خطا در ارسال ویدیو.\n\n"
                f"{tutorial.text_content or 'متن موجود نیست.'}",
                parse_mode="HTML",
                reply_markup=get_tutorial_back_keyboard(tutorial.category),
            )
            return

    # نمایش متن (برای text و faq)
    content = tutorial.text_content or tutorial.title

    await query.edit_message_text(
        content,
        parse_mode="HTML",
        reply_markup=get_tutorial_back_keyboard(tutorial.category),
        disable_web_page_preview=True,
    )


async def tut_inline_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    نمایش راهنمای درون‌مرحله‌ای
    اولویت: ویدیو (اگه هست) > متن
    """
    query = update.callback_query
    await query.answer()

    tutorial_key = query.data.replace("tut_inline_", "")

    async with AsyncSessionLocal() as session:
        tutorial = await get_tutorial_by_key(session, tutorial_key)

    if not tutorial:
        await query.answer(
            "❌ راهنما در دسترس نیست.",
            show_alert=True,
        )
        return

    # اولویت با ویدیو
    if tutorial.video_file_id:
        video_id = tutorial.video_file_id.strip()

        # چک کن file_id درسته
        if not (video_id.startswith("http://") or video_id.startswith("https://")):
            try:
                await context.bot.send_video(
                    chat_id=query.from_user.id,
                    video=video_id,
                    caption=tutorial.video_caption or tutorial.title,
                    parse_mode="HTML",
                )
                await query.answer("✅ ویدیوی راهنما ارسال شد")
                return
            except Exception as e:
                log.error(f"خطا در ارسال ویدیوی راهنما: {e}")
                # اگه ویدیو نتونست، متن رو بفرست

    # اگر ویدیو نبود یا خطا داد، متن بفرست
    content = tutorial.text_content or tutorial.title

    try:
        await context.bot.send_message(
            chat_id=query.from_user.id,
            text=content,
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
        await query.answer("✅ راهنما ارسال شد")
    except Exception as e:
        log.error(f"خطا در ارسال راهنما: {e}")
        await query.answer("❌ خطا در ارسال راهنما", show_alert=True)