"""وحدة الترجمة — تحمّل ملف ar.json وتوفّر دالة tr() للوصول إلى النصوص."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_translations: dict[str, Any] = {}
_loaded = False


def _load() -> None:
    global _translations, _loaded
    if _loaded:
        return
    import sys
    candidates = []
    if hasattr(sys, "_MEIPASS"):
        candidates.append(Path(sys._MEIPASS) / "translations" / "ar.json")
    candidates.extend([
        Path(sys.executable).resolve().parent / "_internal" / "translations" / "ar.json",
        Path(sys.executable).resolve().parent / "translations" / "ar.json",
        Path(__file__).resolve().parent.parent.parent / "translations" / "ar.json",
        Path(__file__).resolve().parent.parent / "translations" / "ar.json",
        Path(__file__).resolve().parent / "translations" / "ar.json",
    ])
    for path in candidates:
        if path.exists():
            try:
                _translations = json.loads(path.read_text(encoding="utf-8"))
                _loaded = True
                return
            except Exception:
                pass
    # احتياطي: القاموس فارغ
    _translations = {}
    _loaded = True


def tr(section: str, key: str, **kwargs: Any) -> str:
    """
    ترجمة نص.

    مثال:
        tr("login", "heading")               → "تسجيل الدخول"
        tr("login", "error_connection_msg", server_url="http://...") → النص مع الاستبدال
    """
    _load()
    try:
        value = _translations[section][key]
    except KeyError:
        # إذا لم يُوجد المفتاح نُعيد مفتاح نصي واضحًا لسهولة الكشف
        return f"[{section}.{key}]"
    if kwargs and isinstance(value, str):
        try:
            return value.format(**kwargs)
        except (KeyError, IndexError):
            return value
    return value


def tr_list(section: str, key: str) -> list[str]:
    """إرجاع قيمة هي قائمة نصوص."""
    _load()
    try:
        value = _translations[section][key]
        return list(value) if isinstance(value, list) else [str(value)]
    except KeyError:
        return []
