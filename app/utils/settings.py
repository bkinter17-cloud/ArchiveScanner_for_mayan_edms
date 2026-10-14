"""إدارة الإعدادات والمسارات والثوابت."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

APP_NAME = "ArchiveScanner"
DOCUMENT_TYPE_ID = int(os.getenv("ARCHIVE_DOCUMENT_TYPE_ID", "4"))
DEFAULT_SERVER = os.getenv("ARCHIVE_SERVER_URL", "http://192.168.234.129:8000")


def application_dir() -> Path:
    """مسار مجلد التطبيق — يعمل سواء من مصدر Python أو ملف PyInstaller المجمّد."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent.parent


def settings_path(write: bool = False) -> Path:
    """
    تحديد مسار ملف الإعدادات.
    - للقراءة: يفضّل الملف بجانب EXE ثم %APPDATA%.
    - للكتابة: يختار المسار الأول القابل للكتابة.
    """
    beside_exe = application_dir() / "settings.json"
    if not write:
        if beside_exe.exists():
            return beside_exe
        app_data_file = (
            Path(os.environ.get("APPDATA", Path.home())) / APP_NAME / "settings.json"
        )
        if app_data_file.exists():
            return app_data_file
        return beside_exe

    # للكتابة
    try:
        if beside_exe.exists():
            if os.access(beside_exe, os.W_OK):
                return beside_exe
        else:
            test_file = application_dir() / ".write_test"
            test_file.touch()
            test_file.unlink()
            return beside_exe
    except OSError:
        pass

    app_data_dir = Path(os.environ.get("APPDATA", Path.home())) / APP_NAME
    app_data_dir.mkdir(parents=True, exist_ok=True)
    return app_data_dir / "settings.json"


def load_settings() -> dict:
    """تحميل الإعدادات من settings.json أو إعادة الافتراضيات."""
    beside_exe = application_dir() / "settings.json"
    if beside_exe.exists():
        try:
            return json.loads(beside_exe.read_text(encoding="utf-8"))
        except Exception:
            pass

    app_data_file = (
        Path(os.environ.get("APPDATA", Path.home())) / APP_NAME / "settings.json"
    )
    if app_data_file.exists():
        try:
            return json.loads(app_data_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    return {"server_url": DEFAULT_SERVER, "document_type_id": DOCUMENT_TYPE_ID}


def save_settings(server_url: str, document_type_id: int = DOCUMENT_TYPE_ID) -> dict:
    """حفظ الإعدادات وإعادة القاموس المحفوظ."""
    data = {
        "server_url": server_url.rstrip("/"),
        "document_type_id": int(document_type_id),
    }
    target = settings_path(write=True)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data


def naps2_path() -> str:
    """تحديد مسار NAPS2.Console.exe."""
    override = os.getenv("NAPS2_CONSOLE", "").strip()
    if override:
        return override
    candidates: list[Path] = []
    if getattr(sys, "frozen", False):
        candidates.append(Path(sys._MEIPASS) / "NAPS2" / "NAPS2.Console.exe")  # type: ignore[attr-defined]
    candidates += [
        application_dir() / "NAPS2" / "NAPS2.Console.exe",
        Path(os.environ.get("PROGRAMFILES", "C:/Program Files"))
        / "NAPS2"
        / "NAPS2.Console.exe",
        Path(os.environ.get("PROGRAMFILES(X86)", "C:/Program Files (x86)"))
        / "NAPS2"
        / "NAPS2.Console.exe",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return "naps2.console"


def logo_path() -> Path | None:
    """تحديد مسار شعار التطبيق."""
    candidates: list[Path] = []
    if getattr(sys, "frozen", False):
        candidates.append(Path(sys._MEIPASS) / "assets" / "logo.png")  # type: ignore[attr-defined]
    candidates += [
        application_dir() / "assets" / "logo.png",
        Path(__file__).resolve().parent.parent.parent / "assets" / "logo.png",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None
