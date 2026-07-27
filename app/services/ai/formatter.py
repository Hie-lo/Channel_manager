"""
تبدیل خروجی خام AI به متن قابل استفاده در پست
"""

from dataclasses import dataclass, field
from app.utils.logger import log


@dataclass
class AIDescription:
    """توضیحات ساختاریافته یک محصول از AI"""
    description: str = ""
    pros: list[str] = field(default_factory=list)
    cons: list[str] = field(default_factory=list)  # "نکات" در ظاهر ولی داخلی cons می‌گیم

    @property
    def is_valid(self) -> bool:
        """چک کن حداقل یک توضیح داره"""
        return bool(self.description.strip())

    def format_for_post(self) -> str:
        """تبدیل به متن قشنگ برای پست"""
        if not self.is_valid:
            return ""

        parts = []

        # توضیح اصلی
        if self.description:
            parts.append(f"📝 {self.description}")

        # مزایا
        if self.pros:
            parts.append("")  # خط خالی
            parts.append("✅ مزایا:")
            for pro in self.pros:
                parts.append(f"• {pro}")

        # نکات
        if self.cons:
            parts.append("")  # خط خالی
            parts.append("⚠️ نکات:")
            for con in self.cons:
                parts.append(f"• {con}")

        return "\n".join(parts)


def parse_ai_response(raw_response: str) -> AIDescription:
    """
    پارس کردن خروجی خام AI
    فرمت انتظار:
        D: توضیح
        P1: مزیت اول
        P2: مزیت دوم
        N1: نکته اول
        N2: نکته دوم
    """
    result = AIDescription()

    if not raw_response or not raw_response.strip():
        return result

    lines = raw_response.strip().split("\n")

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # حذف کاراکترهای اضافی
        if line.startswith("**") and line.endswith("**"):
            line = line[2:-2].strip()

        # پارس D:
        if line.startswith("D:") or line.startswith("D :"):
            content = _extract_content(line)
            if content:
                result.description = content

        # پارس P1, P2, ...
        elif line.startswith(("P1:", "P2:", "P3:", "P1 :", "P2 :", "P3 :")):
            content = _extract_content(line)
            if content:
                result.pros.append(content)

        # پارس N1, N2, ...
        elif line.startswith(("N1:", "N2:", "N3:", "N1 :", "N2 :", "N3 :")):
            content = _extract_content(line)
            if content:
                result.cons.append(content)

    # اگه هیچ ساختار مشخصی نبود، کل متن رو به عنوان description در نظر بگیر
    if not result.is_valid and raw_response.strip():
        # حذف هر خط با فرمت D:/P:/N: احتمالی خراب
        clean_lines = [
            l for l in lines
            if not any(l.strip().startswith(p) for p in ["D:", "P1:", "P2:", "N1:", "N2:"])
        ]
        if clean_lines:
            result.description = " ".join(clean_lines).strip()[:200]

    log.debug(
        f"AI پارس شد: desc={bool(result.description)}, "
        f"pros={len(result.pros)}, cons={len(result.cons)}"
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

    return content