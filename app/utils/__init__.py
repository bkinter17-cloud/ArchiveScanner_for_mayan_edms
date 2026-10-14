"""حزمة app/utils — إدارة الإعدادات، الترجمة، التصميم."""
from .settings import (
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
from .theme import STYLESHEET
from .translations import tr, tr_list

__all__ = [
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
