"""
تبدیل خروجی خام AI به ساختار داده
پشتیبانی از فرمت‌های مختلف بر اساس نوع کسب‌وکار
"""
import re
from dataclasses import dataclass, field
from app.utils.logger import log


@dataclass
class AIDescription:
    """توضیحات ساختاریافته یک محصول از AI"""
    description: str = ""
    # features برای کسب‌وکارهای کامپیوتری (F1-F12)
    features: list[str] = field(default_factory=list)
    # pros برای کسب‌وکارهای عمومی (P1-P5)
    pros: list[str] = field(default_factory=list)
    # cons برای همه کسب‌وکارها (N1-N2)
    cons: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """چک کن حداقل یک توضیح داره"""
        return bool(self.description.strip())

    def format_for_post(self, style: str = "default") -> str:
        """
        تبدیل به متن قشنگ برای پست
        
        DEPRECATED: این متد دیگر استفاده نمی‌شود.
        از placeholder های {ai_description}, {ai_features}, {ai_cons} در قالب استفاده کنید.
        """
        if not self.is_valid:
            return ""

        parts = []

        # توضیح اصلی
        if self.description:
            parts.append(f"📝 {self.description}")

        # ویژگی‌ها (اگر کسب‌وکار کامپیوتری باشه)
        if self.features:
            parts.append("")  # خط خالی
            parts.append("✨ ویژگی‌های خاص:")
            for feature in self.features:
                parts.append(f"🔹 {feature}")

        # مزایا (اگر کسب‌وکار عمومی باشه)
        if self.pros:
            parts.append("")  # خط خالی
            parts.append("✅ مزایا:")
            for pro in self.pros:
                parts.append(f"• {pro}")

        # نکات (محدودیت‌ها)
        if self.cons:
            parts.append("")  # خط خالی
            parts.append("⚠️ ملاحضات:")
            for con in self.cons:
                parts.append(f"• {con}")

        return "\n".join(parts)


def parse_ai_response(raw_response: str, business_key: str = "other") -> AIDescription:
    """
    پارس کردن خروجی خام AI با توجه به نوع کسب‌وکار
    
    فرمت کامپیوتری (computer_shop, laptop_store):
        D: توضیح
        F1-F12: ویژگی‌ها
        N1-N2: محدودیت‌ها
    
    فرمت عمومی (سایر کسب‌وکارها):
        D: توضیح
        P1-P5: مزایا
        N1-N2: محدودیت‌ها
    """
    result = AIDescription()

    if not raw_response or not raw_response.strip():
        return result

    lines = raw_response.strip().split("\n")
    
    # تشخیص نوع کسب‌وکار
    is_computer_business = business_key in ["computer_shop", "laptop_store"]

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # حذف کاراکترهای اضافی
        if line.startswith("**") and line.endswith("**"):
            line = line[2:-2].strip()

        # پارس D: (توضیح اصلی)
        if line.startswith("D:") or line.startswith("D :"):
            content = _extract_content(line)
            if content:
                result.description = content

        # پارس F1-F12 (ویژگی‌ها برای کامپیوتری)
        elif re.match(r'^F\d+\s*:', line):
            if is_computer_business:
                content = _extract_content(line)
                if content:
                    result.features.append(content)

        # پارس P1-P5 (مزایا برای عمومی)
        elif re.match(r'^P\d+\s*:', line):
            if not is_computer_business:
                content = _extract_content(line)
                if content:
                    result.pros.append(content)

        # پارس N1-N2 (محدودیت‌ها برای همه)
        elif re.match(r'^N\d+\s*:', line):
            content = _extract_content(line)
            if content:
                result.cons.append(content)

    # اگه هیچ ساختار مشخصی نبود، کل متن رو به عنوان description در نظر بگیر
    if not result.is_valid and raw_response.strip():
        clean_lines = [
            l for l in lines
            if not any(l.strip().startswith(p) for p in ["D:", "P1:", "P2:", "F1:", "F2:", "N1:", "N2:"])
        ]
        if clean_lines:
            result.description = " ".join(clean_lines).strip()[:200]

    log.debug(
        f"AI پارس شد: desc={bool(result.description)}, "
        f"features={len(result.features)}, pros={len(result.pros)}, cons={len(result.cons)}"
    )

    return result


def _extract_content(line: str) -> str:
    """استخراج محتوای بعد از : در یک خط"""
    if ":" not in line:
        return ""

    content = line.split(":", 1)[1].strip()

    # حذف براکت‌های احتمالی
    content = content.strip("[]").strip()

    # حذف quote های احتمالی
    content = content.strip('"').strip("'").strip()

    # حذف ایموجی‌های تکراری و کاراکترهای اضافی از ابتدا
    import re

    # الگو: ایموجی‌های رایج + bullet + خط تیره + ستاره
    unwanted_prefix_pattern = re.compile(
        r'^[\s📝✅⚠️❌✨🔹•\-\*→↳▪▫◆◇★☆♦♣]+',
        re.UNICODE
    )

    # تا زمانی که تغییر می‌کنه، ادامه بده
    prev = None
    while prev != content:
        prev = content
        content = unwanted_prefix_pattern.sub('', content).strip()

    return content
