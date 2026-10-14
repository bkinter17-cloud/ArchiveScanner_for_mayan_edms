"""
برنامج أرشيف المستندات — نقطة الدخول الرئيسية.

يُستدعى مباشرةً:
    python archive.py
أو بعد التجميد بواسطة PyInstaller.
"""
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from app.client import ArchiveClient
from app.ui import LoginWindow, MainWindow
from app.utils import (
    DEFAULT_SERVER,
    DOCUMENT_TYPE_ID,
    STYLESHEET,
    load_settings,
    logo_path,
)
from app.utils.translations import tr


def main() -> None:
    app = QApplication(sys.argv)
    app.setLayoutDirection(Qt.RightToLeft)
    app.setStyleSheet(STYLESHEET)

    logo = logo_path()
    if logo:
        app.setWindowIcon(QIcon(str(logo)))

    settings = load_settings()
    client = ArchiveClient(
        settings.get("server_url", DEFAULT_SERVER),
        int(settings.get("document_type_id", DOCUMENT_TYPE_ID)),
    )

    login = LoginWindow(client)

    def show_login() -> None:
        login.username_field.clear()
        login.password_field.clear()
        login.status_label.setText(" ")
        login.login_button.setEnabled(True)
        login.login_button.setText(tr("login", "button"))
        login.show()
        login.raise_()
        login.activateWindow()

    def open_main(authed_client: ArchiveClient) -> None:
        window = MainWindow(authed_client)
        window.logout_requested.connect(show_login)
        window.show()
        # نُبقي مرجعًا على النافذة لمنع GC من حذفها
        app.main_window = window  # type: ignore[attr-defined]

    login.logged_in.connect(open_main)
    login.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
