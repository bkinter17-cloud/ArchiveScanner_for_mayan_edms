"""
core.py — طبقة التوافق مع الإصدارات السابقة (Backward Compatibility Shim).

جميع المكوّنات انتقلت إلى حزم منظّمة:
  app/client/   → ArchiveClient, Worker
  app/ui/       → BrandPanel, LoginWindow, …
  app/utils/    → settings, theme, translations

هذا الملف يُوفّر نفس الرموز المُصدَّرة سابقًا حتى لا تنكسر أي أجزاء
خارجية (مثل PyInstaller spec) تستورد من core مباشرةً.
"""

# -- العميل والخيط -----------------------------------------------------------
from app.client.archive_client import ArchiveClient
from app.client.worker          import Worker

# -- عناصر الواجهة ----------------------------------------------------------
from app.ui.widgets      import BrandPanel, apply_shadow, circular_pixmap, field, field_label
from app.ui.login_window import LoginWindow

# -- الإعدادات والمسارات والثوابت -------------------------------------------
from app.utils.settings import (
    APP_NAME,
    DEFAULT_SERVER,
    DOCUMENT_TYPE_ID,
    application_dir,
    load_settings,
    logo_path,
    naps2_path,
    save_settings,
    settings_path,
)

# -- التصميم -----------------------------------------------------------------
from app.utils.theme import STYLESHEET

# -- الترجمة -----------------------------------------------------------------
from app.utils.translations import tr, tr_list

__all__ = [
    # client
    "ArchiveClient",
    "Worker",
    # ui
    "BrandPanel",
    "LoginWindow",
    "apply_shadow",
    "circular_pixmap",
    "field",
    "field_label",
    # settings
    "APP_NAME",
    "DEFAULT_SERVER",
    "DOCUMENT_TYPE_ID",
    "application_dir",
    "load_settings",
    "logo_path",
    "naps2_path",
    "save_settings",
    "settings_path",
    # theme
    "STYLESHEET",
    # translations
    "tr",
    "tr_list",
]
