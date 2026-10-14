"""نافذة تسجيل الدخول — LoginWindow."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QVBoxLayout, QWidget,
)

from app.client import ArchiveClient, Worker
from app.utils.settings import DEFAULT_SERVER, DOCUMENT_TYPE_ID, save_settings
from app.utils.translations import tr, tr_list
from app.ui.widgets import BrandPanel, apply_shadow, circular_pixmap, field, field_label
from app.utils.settings import logo_path


class LoginWindow(QWidget):
    """
    نافذة تسجيل الدخول.
    تُرسل إشارة `logged_in` بكائن ArchiveClient بعد التوثيق الناجح.
    """

    logged_in: Signal = Signal(object)

    def __init__(self, client: ArchiveClient) -> None:
        super().__init__()
        self.client = client
        self.setWindowTitle(tr("login", "window_title"))
        self.setMinimumSize(820, 560)
        self.resize(960, 640)
        self.setLayoutDirection(Qt.RightToLeft)
        self._build_ui()

    # ------------------------------------------------------------------ #
    #  بناء الواجهة                                                        #
    # ------------------------------------------------------------------ #

    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_form_panel(), 1)
        root.addWidget(self._build_brand_panel())
        self.username_field.setFocus()

    # -- لوحة العلامة التجارية (الجانب الأيسر) ----------------------------
    def _build_brand_panel(self) -> QFrame:
        panel = BrandPanel(watermark_size_ratio=0.62, corner="bottom-right", opacity=0.08)
        panel.setObjectName("brandPanel")
        panel.setFixedWidth(360)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(48, 56, 48, 48)
        layout.setAlignment(Qt.AlignRight)
        layout.addStretch(1)

        # شعار دائري
        mark = QLabel()
        mark.setFixedSize(84, 84)
        mark.setAlignment(Qt.AlignCenter)
        logo = logo_path()
        if logo:
            mark.setPixmap(circular_pixmap(logo, 84))
        else:
            mark.setObjectName("brandMark")
            mark.setText("أ")
        layout.addWidget(mark, 0, Qt.AlignRight)
        layout.addSpacing(22)

        # عنوان وشرح
        title = QLabel(tr("login", "brand_title"))
        title.setObjectName("brandTitle")
        title.setWordWrap(True)
        title.setAlignment(Qt.AlignRight)
        layout.addWidget(title)

        subtitle = QLabel(tr("login", "brand_subtitle"))
        subtitle.setObjectName("brandSubtitle")
        subtitle.setWordWrap(True)
        subtitle.setAlignment(Qt.AlignRight)
        layout.addWidget(subtitle)
        layout.addSpacing(34)

        # قائمة المميزات
        for line in tr_list("login", "brand_features"):
            row = QHBoxLayout()
            row.setSpacing(10)
            text = QLabel(line)
            text.setObjectName("brandFeature")
            text.setWordWrap(True)
            text.setAlignment(Qt.AlignRight)
            dot = QLabel("●")
            dot.setObjectName("brandBullet")
            dot.setFixedWidth(14)
            row.addWidget(text, 1)
            row.addWidget(dot, 0, Qt.AlignTop)
            layout.addLayout(row)
            layout.addSpacing(10)

        layout.addStretch(2)
        return panel

    # -- نموذج تسجيل الدخول (الجانب الأيمن) ------------------------------
    def _build_form_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("loginPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(60, 45, 60, 35)
        layout.setAlignment(Qt.AlignRight)
        layout.addStretch(1)

        heading = QLabel(tr("login", "heading"))
        heading.setObjectName("loginHeading")
        heading.setAlignment(Qt.AlignRight | Qt.AlignAbsolute | Qt.AlignVCenter)
        heading.setLayoutDirection(Qt.RightToLeft)
        layout.addWidget(heading, 0, Qt.AlignRight | Qt.AlignAbsolute)

        caption = QLabel(tr("login", "caption"))
        caption.setObjectName("muted")
        caption.setAlignment(Qt.AlignRight | Qt.AlignAbsolute | Qt.AlignVCenter)
        caption.setLayoutDirection(Qt.RightToLeft)
        layout.addWidget(caption, 0, Qt.AlignRight | Qt.AlignAbsolute)
        layout.addSpacing(20)

        # -- عنوان الخادم
        layout.addWidget(
            field_label(tr("login", "server_label")),
            0,
            Qt.AlignRight | Qt.AlignAbsolute,
        )
        self.server_input = QLineEdit()
        self.server_input.setPlaceholderText(tr("login", "server_placeholder"))
        self.server_input.setText(self.client.server_url or DEFAULT_SERVER)
        self.server_input.setLayoutDirection(Qt.LeftToRight)
        self.server_input.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.server_input.setMinimumHeight(42)
        layout.addWidget(self.server_input)
        layout.addSpacing(14)

        # -- اسم المستخدم
        layout.addWidget(
            field_label(tr("login", "username_label")),
            0,
            Qt.AlignRight | Qt.AlignAbsolute,
        )
        self.username_field = field(tr("login", "username_placeholder"))
        layout.addWidget(self.username_field)
        layout.addSpacing(14)

        # -- كلمة المرور
        layout.addWidget(
            field_label(tr("login", "password_label")),
            0,
            Qt.AlignRight | Qt.AlignAbsolute,
        )
        self.password_field = field(tr("login", "password_placeholder"), password=True)
        layout.addWidget(self.password_field)
        layout.addSpacing(16)

        # -- حالة
        self.status_label = QLabel(" ")
        self.status_label.setObjectName("loginStatus")
        self.status_label.setWordWrap(True)
        self.status_label.setAlignment(Qt.AlignRight | Qt.AlignAbsolute | Qt.AlignVCenter)
        self.status_label.setLayoutDirection(Qt.RightToLeft)
        layout.addWidget(self.status_label, 0, Qt.AlignRight | Qt.AlignAbsolute)
        layout.addSpacing(6)

        # -- زر تسجيل الدخول
        self.login_button = QPushButton(tr("login", "button"))
        self.login_button.setObjectName("primaryButton")
        self.login_button.setMinimumHeight(46)
        self.login_button.setCursor(Qt.PointingHandCursor)
        self.login_button.clicked.connect(self._login)
        self.server_input.returnPressed.connect(self._login)
        self.username_field.returnPressed.connect(self._login)
        self.password_field.returnPressed.connect(self._login)
        layout.addWidget(self.login_button)

        layout.addStretch(2)

        server_caption = QLabel(tr("login", "server_caption"))
        server_caption.setObjectName("serverCaption")
        server_caption.setWordWrap(True)
        server_caption.setAlignment(Qt.AlignRight | Qt.AlignAbsolute | Qt.AlignVCenter)
        server_caption.setLayoutDirection(Qt.RightToLeft)
        layout.addWidget(server_caption, 0, Qt.AlignRight | Qt.AlignAbsolute)
        return panel

    # ------------------------------------------------------------------ #
    #  منطق تسجيل الدخول                                                  #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _clean_server_url(raw_url: str) -> str:
        url = str(raw_url or "").strip()
        if not url:
            return ""
        if not (url.startswith("http://") or url.startswith("https://")):
            url = f"http://{url}"
        return url.rstrip("/")

    def _login(self) -> None:
        server_val = self._clean_server_url(self.server_input.text())
        if not server_val:
            self._set_status(tr("login", "error_empty_server"), "error")
            self.server_input.setFocus()
            return

        if not self.username_field.text().strip() or not self.password_field.text():
            self._set_status(tr("login", "error_empty_credentials"), "error")
            return

        self.client.server_url = server_val
        self.server_input.setText(server_val)

        try:
            doc_type_id = getattr(self.client, "document_type_id", DOCUMENT_TYPE_ID)
            save_settings(server_val, doc_type_id)
        except Exception:
            pass

        self.login_button.setEnabled(False)
        self.login_button.setText(tr("login", "connecting"))
        self._set_status(tr("login", "connecting_status"), "info")

        self._worker = Worker(
            self.client.login,
            self.username_field.text().strip(),
            self.password_field.text(),
            parent=self,
        )
        self._worker.finished.connect(lambda _: self._login_ok())
        self._worker.failed.connect(self._login_failed)
        self._worker.start()

    def _set_status(self, text: str, kind: str = "info") -> None:
        self.status_label.setText(text)
        self.status_label.setProperty("state", kind)
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)

    def _login_ok(self) -> None:
        self.password_field.clear()
        self.logged_in.emit(self.client)
        self.close()

    def _login_failed(self, message: str) -> None:
        self._set_status(tr("login", "error_failed"), "error")
        self.login_button.setEnabled(True)
        self.login_button.setText(tr("login", "button"))
        err_lower = str(message).lower()
        if any(
            term in err_lower
            for term in (
                "max retries exceeded",
                "failed to establish a new connection",
                "connection refused",
                "timed out",
                "connecttimeouterror",
            )
        ):
            QMessageBox.critical(
                self,
                tr("login", "error_connection_title"),
                tr("login", "error_connection_msg",
                   server_url=self.client.server_url),
            )
        else:
            QMessageBox.critical(self, tr("login", "error_login_title"), message)
