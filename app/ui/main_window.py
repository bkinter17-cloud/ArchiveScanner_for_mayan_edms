"""النافذة الرئيسية — MainWindow: صفحة الأرشفة وصفحة البحث."""
from __future__ import annotations

import os
import subprocess
import tempfile
import time
import webbrowser
from datetime import date as dt_date
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QComboBox, QFileDialog, QFrame, QHBoxLayout, QLabel,
    QMainWindow, QMessageBox, QPushButton, QScrollArea,
    QSizePolicy, QStackedWidget, QTableWidget, QTableWidgetItem,
    QTextEdit, QVBoxLayout, QWidget,
)

from app.client import ArchiveClient, Worker
from app.utils.settings import naps2_path
from app.utils.settings import logo_path
from app.utils.translations import tr
from app.ui.widgets import (
    BrandPanel, apply_shadow, circular_pixmap, field, field_label,
)


class MainWindow(QMainWindow):
    """
    النافذة الرئيسية للتطبيق.
    تحتوي على:
    - شريط جانبي داكن مع قائمة تنقل.
    - صفحة الأرشفة (مسح / PDF).
    - صفحة البحث مع جدول النتائج.
    """

    # -- TTL لكاش الأجهزة (بالثواني) ---------------------------------------
    _DEVICES_TTL = 120
    logout_requested: Signal = Signal()

    def __init__(self, client: ArchiveClient) -> None:
        super().__init__()
        self.client = client
        self.setWindowTitle(tr("app", "window_title"))
        self.resize(1220, 780)
        self.setMinimumSize(960, 620)
        self.setLayoutDirection(Qt.RightToLeft)

        self.selected_pdf: Path | None = None
        self._devices:    list[str]    = []
        self._devices_fetched_at: float = 0.0

        self._build_ui()

    # ================================================================== #
    #  بناء الهيكل الأساسي للواجهة                                        #
    # ================================================================== #

    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        outer = QHBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # -- المحتوى الرئيسي
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(34, 24, 34, 20)
        content_layout.setSpacing(14)
        content_layout.addLayout(self._build_header())

        # -- صفحات متكدسة
        self.pages     = QStackedWidget()
        self.page_meta: list[tuple[str, str]] = []

        self.archive_page = self._build_archive_page()
        self.search_page  = self._build_search_page()
        self.pages.addWidget(self.archive_page)
        self.page_meta.append((tr("archive_page", "nav_title"), tr("archive_page", "nav_subtitle")))
        self.pages.addWidget(self.search_page)
        self.page_meta.append((tr("search_page", "nav_title"), tr("search_page", "nav_subtitle")))

        content_layout.addWidget(self.pages, 1)
        outer.addWidget(content, 1)
        outer.addWidget(self._build_sidebar())

        # -- ربط زري التنقل
        self.nav_buttons = [self.archive_nav, self.search_nav]
        self.archive_nav.clicked.connect(lambda: self._switch_page(0))
        self.search_nav.clicked.connect(lambda: self._switch_page(1))

        self._refresh_devices()
        self._load_document_types()
        self._set_active_nav(self.archive_nav)

    # ================================================================== #
    #  الشريط الجانبي                                                     #
    # ================================================================== #

    def _build_sidebar(self) -> QWidget:
        sidebar = BrandPanel(watermark_size_ratio=0.34, corner="bottom-right", opacity=0.06)
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(252)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(22, 30, 22, 22)
        side.setSpacing(4)
        side.setAlignment(Qt.AlignRight)

        # -- العلامة التجارية
        brand_row  = QHBoxLayout()
        brand_row.setSpacing(10)
        brand_text = QVBoxLayout()
        brand_text.setSpacing(0)
        brand = QLabel(tr("app", "name"))
        brand.setObjectName("brand")
        brand_caption = QLabel(tr("app", "caption"))
        brand_caption.setObjectName("brandCaption")
        brand_text.addWidget(brand)
        brand_text.addWidget(brand_caption)
        brand_row.addStretch()
        brand_row.addLayout(brand_text)
        mark = QLabel()
        mark.setFixedSize(42, 42)
        mark.setAlignment(Qt.AlignCenter)
        logo = logo_path()
        if logo:
            mark.setPixmap(circular_pixmap(logo, 42))
        else:
            mark.setObjectName("sidebarMark")
            mark.setText("أ")
        brand_row.addWidget(mark)
        side.addLayout(brand_row)
        side.addSpacing(30)

        # -- أزرار التنقل
        self.archive_nav = QPushButton(tr("sidebar", "nav_archive"))
        self.search_nav  = QPushButton(tr("sidebar", "nav_search"))
        for btn in (self.archive_nav, self.search_nav):
            btn.setObjectName("navButton")
            btn.setMinimumHeight(46)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setLayoutDirection(Qt.RightToLeft)
            side.addWidget(btn)
        side.addStretch()

        # -- فاصل
        divider = QFrame()
        divider.setObjectName("sidebarDivider")
        divider.setFixedHeight(1)
        side.addWidget(divider)
        side.addSpacing(14)

        # -- معلومات المستخدم
        user_row  = QHBoxLayout()
        user_row.setSpacing(10)
        user_text = QVBoxLayout()
        user_text.setSpacing(0)
        user_name  = QLabel(self.client.username or "—")
        user_name.setObjectName("userName")
        user_state = QLabel(tr("sidebar", "connected"))
        user_state.setObjectName("userState")
        user_text.addWidget(user_name)
        user_text.addWidget(user_state)
        user_row.addStretch()
        user_row.addLayout(user_text)
        initial = (self.client.username or "?")[:1].upper()
        avatar  = QLabel(initial)
        avatar.setObjectName("avatarBadge")
        avatar.setFixedSize(36, 36)
        avatar.setAlignment(Qt.AlignCenter)
        user_row.addWidget(avatar)
        side.addLayout(user_row)
        side.addSpacing(10)

        logout = QPushButton(tr("sidebar", "logout"))
        logout.setObjectName("logoutButton")
        logout.setMinimumHeight(40)
        logout.setCursor(Qt.PointingHandCursor)
        logout.clicked.connect(self._logout)
        side.addWidget(logout)

        return sidebar

    # ================================================================== #
    #  الترويسة                                                           #
    # ================================================================== #

    def _build_header(self) -> QHBoxLayout:
        header = QHBoxLayout()
        header.setSpacing(14)

        self.status_chip = QLabel(tr("header", "status_ready"))
        self.status_chip.setObjectName("statusChip")
        self.status_chip.setProperty("state", "neutral")
        header.addWidget(self.status_chip, 0, Qt.AlignVCenter)

        server_chip = QLabel(f"🖥  {self.client.server_url}")
        server_chip.setObjectName("chip")
        header.addWidget(server_chip, 0, Qt.AlignVCenter)

        header.addStretch()

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        self.page_title = QLabel(tr("archive_page", "nav_title"))
        self.page_title.setObjectName("pageTitle")
        self.page_title.setAlignment(Qt.AlignRight | Qt.AlignAbsolute | Qt.AlignVCenter)
        self.page_title.setLayoutDirection(Qt.RightToLeft)
        self.page_subtitle = QLabel(tr("archive_page", "nav_subtitle"))
        self.page_subtitle.setObjectName("pageSubtitle")
        self.page_subtitle.setAlignment(Qt.AlignRight | Qt.AlignAbsolute | Qt.AlignVCenter)
        self.page_subtitle.setLayoutDirection(Qt.RightToLeft)
        title_box.addWidget(self.page_title, 0, Qt.AlignRight | Qt.AlignAbsolute)
        title_box.addWidget(self.page_subtitle, 0, Qt.AlignRight | Qt.AlignAbsolute)
        header.addLayout(title_box)
        return header

    # ================================================================== #
    #  مساعدات التخطيط                                                    #
    # ================================================================== #

    @staticmethod
    def _card() -> QFrame:
        frame = QFrame()
        frame.setObjectName("card")
        apply_shadow(frame, blur=32, y_offset=12, opacity=28)
        return frame

    @staticmethod
    def _section_title(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("sectionTitle")
        label.setAlignment(Qt.AlignRight | Qt.AlignAbsolute | Qt.AlignVCenter)
        label.setLayoutDirection(Qt.RightToLeft)
        return label

    @staticmethod
    def _divider() -> QFrame:
        line = QFrame()
        line.setObjectName("divider")
        line.setFixedHeight(1)
        return line

    @staticmethod
    def _make_field_group(label_text: str, widget: QWidget) -> QVBoxLayout:
        grp = QVBoxLayout()
        grp.setSpacing(6)
        grp.addWidget(field_label(label_text), 0, Qt.AlignRight | Qt.AlignAbsolute)
        grp.addWidget(widget)
        return grp

    # ================================================================== #
    #  صفحة الأرشفة                                                       #
    # ================================================================== #

    def _build_archive_page(self) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setLayoutDirection(Qt.RightToLeft)

        page = QWidget()
        page.setObjectName("archivePageInner")
        page.setLayoutDirection(Qt.RightToLeft)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        card        = self._card()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(34, 28, 34, 28)
        card_layout.setSpacing(14)

        # -- قسم بيانات المستند
        card_layout.addWidget(self._section_title(tr("archive_page", "section_meta")))

        self.title_field = field(tr("archive_page", "field_title_placeholder"))
        self.number_field = field(tr("archive_page", "field_number_placeholder"))
        self.date_field   = field(tr("archive_page", "field_date_placeholder"))
        try:
            self.date_field.setText(dt_date.today().strftime("%Y-%m-%d"))
        except Exception:
            pass

        for editor in (self.title_field, self.number_field, self.date_field):
            editor.setMinimumHeight(44)

        self.notes_field = QTextEdit()
        self.notes_field.setPlaceholderText(tr("archive_page", "field_notes_placeholder"))
        self.notes_field.setMinimumHeight(76)
        self.notes_field.setMaximumHeight(96)
        self.notes_field.setLayoutDirection(Qt.RightToLeft)

        card_layout.addLayout(
            self._make_field_group(tr("archive_page", "field_title"), self.title_field)
        )

        # -- رقم المستند والتاريخ جنبًا إلى جنب مع حماية من التداخل
        num_date_row = QHBoxLayout()
        num_date_row.setSpacing(16)

        num_grp = self._make_field_group(
            tr("archive_page", "field_number"), self.number_field
        )
        date_grp = self._make_field_group(
            tr("archive_page", "field_date"), self.date_field
        )
        # تحديد عرض أدنى لمنع ضغط الحقول عند تصغير النافذة
        self.number_field.setMinimumWidth(140)
        self.date_field.setMinimumWidth(120)

        num_date_row.addLayout(num_grp, 1)
        num_date_row.addLayout(date_grp, 1)
        card_layout.addLayout(num_date_row)

        card_layout.addLayout(
            self._make_field_group(tr("archive_page", "field_notes"), self.notes_field)
        )

        card_layout.addSpacing(4)
        card_layout.addWidget(self._divider())
        card_layout.addSpacing(6)

        # -- قسم خيارات الأرشفة
        card_layout.addWidget(self._section_title(tr("archive_page", "section_options")))
        options_row = QHBoxLayout()
        options_row.setSpacing(16)

        # جهاز الماسح
        device_box = QVBoxLayout()
        device_box.setSpacing(6)
        device_box.addWidget(
            field_label(tr("archive_page", "field_device")),
            0,
            Qt.AlignRight | Qt.AlignAbsolute,
        )
        device_row = QHBoxLayout()
        device_row.setSpacing(8)
        self.device_combo = QComboBox()
        self.device_combo.setMinimumHeight(42)
        self.device_combo.setMinimumWidth(120)
        self.device_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.device_refresh_button = QPushButton(tr("archive_page", "btn_refresh"))
        self.device_refresh_button.setObjectName("ghostButton")
        self.device_refresh_button.setMinimumHeight(42)
        self.device_refresh_button.setCursor(Qt.PointingHandCursor)
        self.device_refresh_button.clicked.connect(self._refresh_devices_forced)
        device_row.addWidget(self.device_combo, 1)
        device_row.addWidget(self.device_refresh_button)
        device_box.addLayout(device_row)
        options_row.addLayout(device_box, 1)

        # نوع المستند
        type_box = QVBoxLayout()
        type_box.setSpacing(6)
        type_box.addWidget(
            field_label(tr("archive_page", "field_doc_type")),
            0,
            Qt.AlignRight | Qt.AlignAbsolute,
        )
        type_row = QHBoxLayout()
        type_row.setSpacing(8)
        self.document_type_combo = QComboBox()
        self.document_type_combo.setMinimumHeight(42)
        self.document_type_combo.setMinimumWidth(120)
        self.document_type_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.document_type_combo.addItem(tr("document_types", "loading"), None)
        self.type_refresh_button = QPushButton(tr("archive_page", "btn_refresh"))
        self.type_refresh_button.setObjectName("ghostButton")
        self.type_refresh_button.setMinimumHeight(42)
        self.type_refresh_button.setCursor(Qt.PointingHandCursor)
        self.type_refresh_button.clicked.connect(self._load_document_types_forced)
        type_row.addWidget(self.document_type_combo, 1)
        type_row.addWidget(self.type_refresh_button)
        type_box.addLayout(type_row)
        options_row.addLayout(type_box, 1)

        card_layout.addLayout(options_row)

        # -- شريط الملف المختار
        self.file_label = QLabel(tr("archive_page", "file_none"))
        self.file_label.setObjectName("filePill")
        self.file_label.setAlignment(Qt.AlignCenter)
        self.file_label.setWordWrap(True)
        card_layout.addWidget(self.file_label)

        card_layout.addSpacing(4)
        card_layout.addWidget(self._divider())
        card_layout.addSpacing(8)

        # -- أزرار الأرشفة
        actions = QHBoxLayout()
        actions.setSpacing(12)
        self.scan_button = QPushButton(tr("archive_page", "btn_scan"))
        self.scan_button.setObjectName("successButton")
        self.pdf_button  = QPushButton(tr("archive_page", "btn_pdf"))
        self.pdf_button.setObjectName("primaryButton")
        for btn in (self.pdf_button, self.scan_button):
            btn.setMinimumHeight(46)
            btn.setCursor(Qt.PointingHandCursor)
        self.scan_button.clicked.connect(self._scan_and_archive)
        self.pdf_button.clicked.connect(self._choose_and_archive_pdf)
        actions.addWidget(self.scan_button)
        actions.addWidget(self.pdf_button)
        actions.addStretch()
        card_layout.addLayout(actions)

        layout.addWidget(card)
        layout.addStretch()
        scroll.setWidget(page)
        return scroll

    # ================================================================== #
    #  صفحة البحث                                                         #
    # ================================================================== #

    def _build_search_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)

        card        = self._card()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(34, 30, 34, 30)
        card_layout.setSpacing(14)

        card_layout.addWidget(self._section_title(tr("search_page", "section_title")))

        row = QHBoxLayout()
        row.setSpacing(10)
        self.query_field = field(tr("search_page", "query_placeholder"))
        self.query_field.returnPressed.connect(self._search)
        self.search_button = QPushButton(tr("search_page", "btn_search"))
        self.search_button.setObjectName("primaryButton")
        self.search_button.setMinimumHeight(42)
        self.search_button.setMinimumWidth(110)
        self.search_button.setCursor(Qt.PointingHandCursor)
        self.search_button.clicked.connect(self._search)
        row.addWidget(self.search_button)
        row.addWidget(self.query_field, 1)
        card_layout.addLayout(row)

        self.results_caption = QLabel(tr("search_page", "no_results"))
        self.results_caption.setObjectName("muted")
        self.results_caption.setAlignment(Qt.AlignRight | Qt.AlignAbsolute | Qt.AlignVCenter)
        self.results_caption.setLayoutDirection(Qt.RightToLeft)
        card_layout.addWidget(self.results_caption, 0, Qt.AlignRight | Qt.AlignAbsolute)

        hint = QLabel(tr("search_page", "hint_dbl_click"))
        hint.setObjectName("muted")
        hint.setAlignment(Qt.AlignRight | Qt.AlignAbsolute | Qt.AlignVCenter)
        hint.setLayoutDirection(Qt.RightToLeft)
        card_layout.addWidget(hint, 0, Qt.AlignRight | Qt.AlignAbsolute)

        # -- الجدول
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels([
            tr("search_page", "col_number"),
            tr("search_page", "col_subject"),
            tr("search_page", "col_description"),
        ])
        self.table.setColumnWidth(0, 180)
        self.table.setColumnWidth(1, 300)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.cellDoubleClicked.connect(self._open_result)
        self.table.setLayoutDirection(Qt.RightToLeft)
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        card_layout.addWidget(self.table)

        layout.addWidget(card)
        return page

    # ================================================================== #
    #  إدارة الحالة والتنقل                                               #
    # ================================================================== #

    def _switch_page(self, index: int) -> None:
        self.pages.setCurrentIndex(index)
        self._set_active_nav(self.nav_buttons[index])
        title, subtitle = self.page_meta[index]
        self.page_title.setText(title)
        self.page_subtitle.setText(subtitle)

    def _set_active_nav(self, active_button: QPushButton) -> None:
        for btn in self.nav_buttons:
            btn.setObjectName("navActive" if btn is active_button else "navButton")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _set_status(self, text: str, kind: str = "neutral") -> None:
        self.status_chip.setText(text)
        self.status_chip.setProperty("state", kind)
        self.status_chip.style().unpolish(self.status_chip)
        self.status_chip.style().polish(self.status_chip)

    def _set_busy(self, busy: bool, text: str) -> None:
        self.scan_button.setEnabled(not busy)
        self.pdf_button.setEnabled(not busy)
        self._set_status(text, "busy" if busy else "neutral")

    def _logout(self) -> None:
        """إنهاء الجلسة والعودة الآمنة إلى شاشة تسجيل الدخول."""
        answer = QMessageBox.question(
            self,
            tr("sidebar", "logout_confirm_title"),
            tr("sidebar", "logout_confirm_message"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        self.client.logout()
        self.logout_requested.emit()
        self.close()

    # ================================================================== #
    #  تشغيل العمليات بشكل غير متزامن                                     #
    # ================================================================== #

    def _run_async(self, function, success, failure) -> None:
        worker = Worker(function, parent=self)
        worker.finished.connect(success)
        worker.failed.connect(failure)
        worker.finished.connect(worker.deleteLater)
        worker.failed.connect(worker.deleteLater)
        worker.start()

    # ================================================================== #
    #  أجهزة الماسح — مع Caching                                          #
    # ================================================================== #

    def _refresh_devices(self, force: bool = False) -> None:
        """تحديث قائمة الأجهزة مع احترام TTL الكاش (إلا إذا force=True)."""
        now = time.monotonic()
        if (
            not force
            and self._devices
            and (now - self._devices_fetched_at) < self._DEVICES_TTL
        ):
            return  # استخدام الكاش

        self.device_combo.clear()
        self.device_combo.addItem(tr("devices", "detecting"))
        self.device_combo.setEnabled(False)
        self.device_refresh_button.setEnabled(False)

        def list_devices() -> list[str]:
            result = subprocess.run(
                [naps2_path(), "--listdevices"],
                capture_output=True,
                text=True,
                timeout=30,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            output  = (result.stdout or result.stderr or "").strip()
            devices = [line.strip() for line in output.splitlines() if line.strip()]
            if result.returncode != 0 or not devices:
                raise RuntimeError(
                    output or tr("devices", "not_found_error")
                )
            return devices

        self._run_async(list_devices, self._devices_loaded, self._devices_failed)

    def _refresh_devices_forced(self) -> None:
        self._refresh_devices(force=True)

    def _devices_loaded(self, devices: list[str]) -> None:
        self._devices = devices
        self._devices_fetched_at = time.monotonic()
        self.device_combo.clear()
        self.device_combo.addItems(devices)
        self.device_combo.setEnabled(True)
        self.device_refresh_button.setEnabled(True)
        self._set_status(
            tr("devices", "found_status", count=len(devices)), "success"
        )

    def _devices_failed(self, _message: str) -> None:
        self._devices = []
        self.device_combo.clear()
        self.device_combo.addItem(tr("devices", "not_found_item"))
        self.device_combo.setEnabled(False)
        self.device_refresh_button.setEnabled(True)
        self._set_status(tr("devices", "none_status"), "error")

    # ================================================================== #
    #  أنواع المستندات — مع Caching عبر ArchiveClient                     #
    # ================================================================== #

    def _load_document_types(self, force: bool = False) -> None:
        self._set_status(tr("document_types", "loading_status"), "busy")
        self.document_type_combo.setEnabled(False)
        self.type_refresh_button.setEnabled(False)
        self._run_async(
            lambda: self.client.document_types(force_refresh=force),
            self._document_types_loaded,
            self._document_types_failed,
        )

    def _load_document_types_forced(self) -> None:
        self._load_document_types(force=True)

    def _document_types_loaded(self, types: list[dict]) -> None:
        if not types:
            self._document_types_failed(tr("document_types", "none_error"))
            return
        self.document_type_combo.clear()
        selected_index = 0
        for index, item in enumerate(types):
            type_id = int(item["id"])
            self.document_type_combo.addItem(
                f"{item['label']}  (ID {type_id})", type_id
            )
            if type_id == int(self.client.document_type_id):
                selected_index = index
        self.document_type_combo.setCurrentIndex(selected_index)
        self.client.document_type_id = int(self.document_type_combo.currentData())
        self.document_type_combo.setEnabled(True)
        self.type_refresh_button.setEnabled(True)
        self._set_status(
            tr("document_types", "loaded_status",
               name=self.document_type_combo.currentText()),
            "neutral",
        )

    def _document_types_failed(self, message: str) -> None:
        self.document_type_combo.clear()
        self.document_type_combo.addItem(tr("document_types", "failed_item"), None)
        self.document_type_combo.setEnabled(False)
        self.type_refresh_button.setEnabled(True)
        self._set_status(tr("document_types", "failed_status"), "error")
        QMessageBox.warning(self, tr("document_types", "failed_title"), message)

    # ================================================================== #
    #  منطق الأرشفة                                                       #
    # ================================================================== #

    def _selected_document_type(self) -> int:
        value = self.document_type_combo.currentData()
        if value is None:
            raise RuntimeError(tr("archive_page", "error_no_doc_type"))
        return int(value)

    def _metadata(self) -> tuple[str, str, str, str]:
        number = self.number_field.text().strip()
        title  = self.title_field.text().strip()
        date   = self.date_field.text().strip()
        for editor, value in (
            (self.number_field, number),
            (self.title_field, title),
            (self.date_field, date),
        ):
            editor.setProperty("invalid", not bool(value))
            editor.style().unpolish(editor)
            editor.style().polish(editor)
        if not number or not title or not date:
            raise RuntimeError(tr("archive_page", "error_required_fields"))
        try:
            dt_date.fromisoformat(date)
        except ValueError:
            self.date_field.setProperty("invalid", True)
            self.date_field.style().unpolish(self.date_field)
            self.date_field.style().polish(self.date_field)
            raise RuntimeError(tr("archive_page", "error_invalid_date"))
        return number, title, date, self.notes_field.toPlainText().strip()

    def _choose_and_archive_pdf(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            tr("archive_page", "dialog_pdf_title"),
            "",
            tr("archive_page", "dialog_pdf_filter"),
        )
        if not path:
            return
        self.selected_pdf = Path(path)
        if not self.selected_pdf.is_file() or self.selected_pdf.stat().st_size == 0:
            self.selected_pdf = None
            QMessageBox.warning(
                self, tr("archive_page", "error_file_title"),
                tr("archive_page", "error_file_empty"),
            )
            return
        self.file_label.setText(
            tr("archive_page", "file_selected", filename=self.selected_pdf.name)
        )
        try:
            document_type_id = self._selected_document_type()
            number, title, date, notes = self._metadata()
        except RuntimeError as error:
            QMessageBox.warning(self, tr("archive_page", "error_incomplete_title"), str(error))
            return
        self._set_busy(True, tr("archive_page", "status_uploading_pdf"))
        self._run_async(
            lambda: self.client.archive(
                self.selected_pdf, number, title, date, notes, document_type_id
            ),
            lambda result: self._archive_success(
                result, tr("archive_page", "success_pdf_msg")
            ),
            self._archive_failed,
        )

    def _scan_and_archive(self) -> None:
        if not self._devices:
            QMessageBox.warning(
                self,
                tr("archive_page", "error_no_device_title"),
                tr("archive_page", "error_no_device_msg"),
            )
            return
        try:
            document_type_id = self._selected_document_type()
            number, title, date, notes = self._metadata()
        except RuntimeError as error:
            QMessageBox.warning(self, tr("archive_page", "error_incomplete_title"), str(error))
            return

        device = self.device_combo.currentText()
        self._set_busy(True, tr("archive_page", "status_scanning"))

        def scan_upload():
            temp_path: Path | None = None
            try:
                with tempfile.NamedTemporaryFile(
                    prefix="archive_scan_", suffix=".pdf", delete=False
                ) as temp:
                    temp_path = Path(temp.name)
                result = subprocess.run(
                    [naps2_path(), "--device", device, "-o", str(temp_path), "--force"],
                    capture_output=True,
                    text=True,
                    timeout=180,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
                if (
                    result.returncode != 0
                    or not temp_path.exists()
                    or temp_path.stat().st_size == 0
                ):
                    raise RuntimeError(
                        result.stderr or result.stdout
                        or tr("client_errors", "scan_failed")
                    )
                return self.client.archive(
                    temp_path, number, title, date, notes, document_type_id
                )
            finally:
                if temp_path and temp_path.exists():
                    temp_path.unlink(missing_ok=True)

        self._run_async(
            scan_upload,
            lambda result: self._archive_success(
                result, tr("archive_page", "success_scan_msg")
            ),
            self._archive_failed,
        )

    def _archive_success(self, _result, message: str) -> None:
        self._set_busy(False, tr("header", "status_ready"))
        self._set_status(message, "success")
        self.number_field.clear()
        self.title_field.clear()
        try:
            self.date_field.setText(dt_date.today().strftime("%Y-%m-%d"))
        except Exception:
            self.date_field.clear()
        self.notes_field.clear()
        self.selected_pdf = None
        self.file_label.setText(tr("archive_page", "file_none"))
        QMessageBox.information(self, tr("archive_page", "success_title"), message)

    def _archive_failed(self, message: str) -> None:
        self._set_busy(False, tr("archive_page", "status_failed"))
        self._set_status(tr("archive_page", "status_failed"), "error")
        QMessageBox.critical(self, tr("archive_page", "error_archive_title"), message)

    # ================================================================== #
    #  منطق البحث                                                         #
    # ================================================================== #

    def _search(self) -> None:
        query = self.query_field.text().strip()
        if not query:
            self.query_field.setFocus()
            return
        self.search_button.setEnabled(False)
        self.query_field.setEnabled(False)
        self._set_status(tr("search_page", "status_searching"), "busy")
        self._run_async(
            lambda: self.client.search(query),
            self._show_results,
            self._search_failed,
        )

    def _show_results(self, items: list[dict]) -> None:
        self.search_button.setEnabled(True)
        self.query_field.setEnabled(True)
        self.table.setRowCount(0)
        for raw in items:
            item  = self.client._unwrap_document(raw)
            row   = self.table.rowCount()
            self.table.insertRow(row)
            label = str(item.get("label", ""))
            if " - " in label:
                book_number, subject = label.split(" - ", 1)
            else:
                book_number = subject = label
            values = [book_number, subject, item.get("description", "")]
            for col, value in enumerate(values):
                cell = QTableWidgetItem(str(value))
                cell.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                if col == 0:
                    cell.setData(Qt.UserRole, item.get("id"))
                self.table.setItem(row, col, cell)
        count = len(items)
        self.results_caption.setText(
            tr("search_page", "results_found", count=count)
            if items
            else tr("search_page", "results_none")
        )
        self._set_status(
            tr("search_page", "status_found", count=count),
            "success" if items else "neutral",
        )

    def _search_failed(self, message: str) -> None:
        self.search_button.setEnabled(True)
        self.query_field.setEnabled(True)
        self._set_status(tr("search_page", "status_search_failed"), "error")
        QMessageBox.critical(self, tr("search_page", "error_search_title"), message)

    def _open_result(self, row: int, _column: int) -> None:
        id_item     = self.table.item(row, 0)
        document_id = id_item.data(Qt.UserRole) if id_item else None
        if document_id is None:
            QMessageBox.warning(
                self,
                tr("search_page", "open_doc_title"),
                tr("search_page", "doc_id_missing"),
            )
            return
        self._set_status(tr("search_page", "status_downloading"), "busy")
        self._run_async(
            lambda: self.client.download_document(document_id),
            self._open_local_document,
            self._open_document_failed,
        )

    def _open_local_document(self, local_path: str) -> None:
        self._set_status(tr("search_page", "status_downloaded"), "success")
        try:
            if hasattr(os, "startfile"):
                os.startfile(local_path)
            else:
                webbrowser.open(Path(local_path).as_uri())
        except Exception as error:
            QMessageBox.critical(
                self,
                tr("search_page", "open_doc_title"),
                tr("search_page", "open_failed_msg",
                   path=local_path, error=error),
            )

    def _open_document_failed(self, message: str) -> None:
        self._set_status(tr("search_page", "status_download_failed"), "error")
        QMessageBox.critical(self, tr("search_page", "open_doc_title"), message)
