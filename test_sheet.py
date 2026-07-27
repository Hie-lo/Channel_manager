"""
تست دستی اتصال به Google Sheet
این فایل رو بعد از تست حذف کن
"""

import asyncio
import gspread
from google.oauth2.service_account import Credentials
from pathlib import Path

# تنظیمات
CREDENTIALS_FILE = "secrets/google_service_account.json"

# ⚠️ لینک شیتت رو اینجا بذار
SHEET_URL = "https://docs.google.com/spreadsheets/d/1WDHERQgp7WiHBMci8XSgPh0m76xzs_k-/edit?usp=sharing&ouid=114113507325068196443&rtpof=true&sd=true"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]


def extract_sheet_id(url):
    import re
    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", url)
    if match:
        return match.group(1)
    return None


def main():
    print("🔍 تست اتصال به Google Sheet\n")

    # چک credentials
    creds_path = Path(CREDENTIALS_FILE)
    if not creds_path.exists():
        print(f"❌ فایل credentials پیدا نشد: {creds_path}")
        return
    print(f"✅ فایل credentials موجود است")

    # ساخت client
    try:
        creds = Credentials.from_service_account_file(
            str(creds_path),
            scopes=SCOPES,
        )
        client = gspread.authorize(creds)
        print("✅ اتصال به Google API برقرار شد")
    except Exception as e:
        print(f"❌ خطا در ساخت client: {e}")
        return

    # استخراج ID
    sheet_id = extract_sheet_id(SHEET_URL)
    if not sheet_id:
        print(f"❌ ID شیت استخراج نشد از: {SHEET_URL}")
        return
    print(f"✅ ID شیت: {sheet_id}")

    # باز کردن شیت
    try:
        print(f"\n🔍 در حال باز کردن شیت...")
        spreadsheet = client.open_by_key(sheet_id)
        print(f"✅ شیت باز شد!")
        print(f"   عنوان: {spreadsheet.title}")
        print(f"   ID: {spreadsheet.id}")

        # لیست worksheet ها
        print(f"\n📄 لیست صفحه‌ها:")
        for ws in spreadsheet.worksheets():
            print(f"   • {ws.title} ({ws.row_count} ردیف × {ws.col_count} ستون)")

        # خواندن اولین worksheet
        print(f"\n🔍 خواندن اولین صفحه...")
        first_ws = spreadsheet.sheet1
        values = first_ws.get_all_values()
        print(f"✅ {len(values)} ردیف خوانده شد")

        if values:
            print(f"\n📋 ردیف اول (هدر):")
            for i, cell in enumerate(values[0]):
                print(f"   ستون {i+1}: {cell}")

    except gspread.exceptions.SpreadsheetNotFound:
        print(f"\n❌ شیت پیدا نشد!")
        print("   دلایل احتمالی:")
        print("   1. لینک اشتباهه")
        print("   2. ایمیل ربات به شیت دسترسی نداره")

    except gspread.exceptions.APIError as e:
        print(f"\n❌ خطای API:")
        print(f"   {e}")
        print(f"\n   جزئیات کامل:")
        print(f"   {str(e)}")

    except Exception as e:
        print(f"\n❌ خطای غیرمنتظره:")
        print(f"   نوع: {type(e).__name__}")
        print(f"   پیام: {e}")


if __name__ == "__main__":
    main()