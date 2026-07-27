"""
تست دستی AI - فقط برای اطمینان از اتصال
این فایل رو بعد از تست حذف کن
"""

import asyncio
from app.services.ai.provider import call_ai


async def main():
    print("🤖 تست اتصال به OpenRouter...\n")

    result = await call_ai(
        system_prompt="تو یک دستیار مفید هستی. کوتاه پاسخ بده.",
        user_prompt="سلام! برای تست، فقط بنویس: 'اتصال برقرار است'",
        max_tokens=50,
    )

    if result.success:
        print(f"✅ موفق!\n")
        print(f"پاسخ: {result.content}")
        print(f"توکن مصرف شده: {result.tokens_used}")
    else:
        print(f"❌ خطا: {result.error_message}")


if __name__ == "__main__":
    asyncio.run(main())