"""
زمان‌بند مرکزی پروژه
همه Jobهای دوره‌ای اینجا ثبت می‌شن
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from app.utils.logger import log


# نمونه سراسری scheduler
_scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler:
    """گرفتن نمونه scheduler"""
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(
            timezone="Asia/Tehran",  # زمان ایران
        )
    return _scheduler


def start_scheduler(bot) -> None:
    """راه‌اندازی scheduler و ثبت همه Jobها"""
    from app.tasks.jobs.publish_job import run_auto_publish_job
    from app.tasks.jobs.subscription_job import run_subscription_reminder_job
    from app.tasks.jobs.sheet_sync_job import run_sheet_sync_job

    scheduler = get_scheduler()

    # ─── Job 1: انتشار خودکار محصولات ───
    scheduler.add_job(
        run_auto_publish_job,
        trigger=IntervalTrigger(minutes=5),
        args=[bot],
        id="auto_publish",
        name="انتشار خودکار محصولات",
        replace_existing=True,
        max_instances=1,
    )
    log.info("✅ Job 'انتشار خودکار محصولات' ثبت شد (هر ۵ دقیقه)")

    # ─── Job 2: یادآوری انقضای اشتراک ───
    scheduler.add_job(
        run_subscription_reminder_job,
        trigger=CronTrigger(hour=10, minute=0),
        args=[bot],
        id="subscription_reminder",
        name="یادآوری انقضای اشتراک",
        replace_existing=True,
        max_instances=1,
    )
    log.info("✅ Job 'یادآوری انقضای اشتراک' ثبت شد (روزانه ساعت ۱۰)")

    # ─── Job 3: همگام‌سازی Google Sheet ───
    # هر ۲ ساعت (به هر مشتری بر اساس business config اجازه sync میده)
    scheduler.add_job(
        run_sheet_sync_job,
        trigger=IntervalTrigger(hours=2),
        args=[bot],
        id="sheet_sync",
        name="همگام‌سازی Google Sheet",
        replace_existing=True,
        max_instances=1,
    )
    log.info("✅ Job 'همگام‌سازی Google Sheet' ثبت شد (هر ۲ ساعت)")

    scheduler.start()
    log.info("🚀 Scheduler راه‌اندازی شد")


def shutdown_scheduler() -> None:
    """توقف scheduler"""
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        log.info("🛑 Scheduler متوقف شد")