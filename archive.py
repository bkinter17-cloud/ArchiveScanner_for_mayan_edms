"""DocArchive Scanner — scan/upload documents and search the archive."""
import os
import subprocess
import sys
import tempfile
import webbrowser
from pathlib import Path

from core import (
    ArchiveClient, Worker, LoginWindow, BrandPanel, STYLESHEET,
    apply_shadow, field, field_label, logo_path, circular_pixmap,
    load_settings, naps2_path, DEFAULT_SERVER, DOCUMENT_TYPE_ID,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication, QComboBox, QFileDialog, QFrame, QGridLayout, QHBoxLayout,
    QLabel, QMainWindow, QMessageBox, QPushButton, QStackedWidget,
    QTableWidget, QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget
)


class MainWindow(QMainWindow):
    def __init__(self, client):
        super().__init__()
        self.client = client
        self.setWindowTitle("DocArchive | Document Scanner & Archiving")
        self.resize(1220, 780)
        self.setMinimumSize(980, 640)
        self.setLayoutDirection(Qt.LeftToRight)
        self.selected_pdf = None
        self.devices = []
        self.build_ui()

    # -- layout ------------------------------------------------------------
    def build_ui(self):
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        outer = QHBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self.build_sidebar())

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(38, 32, 38, 28)
        content_layout.setSpacing(18)
        content_layout.addLayout(self.build_header())

        self.pages = QStackedWidget()
        self.page_meta = []
        self.archive_page = self.build_archive_page()
        self.search_page = self.build_search_page()
        self.pages.addWidget(self.archive_page)
        self.page_meta.append(("Archive Document", "Scan a document or upload a PDF file for digital archiving"))
        self.pages.addWidget(self.search_page)
        self.page_meta.append(("Search Archives", "Search by document number, title, or keywords across indexed files"))
        content_layout.addWidget(self.pages)
        outer.addWidget(content, 1)

        self.nav_buttons = [self.archive_nav, self.search_nav]
        self.archive_nav.clicked.connect(lambda: self.switch_page(0))
        self.search_nav.clicked.connect(lambda: self.switch_page(1))

        self.refresh_devices()
        self.load_document_types()
        self.set_active_nav(self.archive_nav)

    def build_sidebar(self):
        sidebar = BrandPanel(watermark_size_ratio=0.34, corner="bottom-left", opacity=0.06)
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(252)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(22, 30, 22, 22)
        side.setSpacing(4)

        brand_row = QHBoxLayout()
        brand_row.setSpacing(10)
        mark = QLabel()
        mark.setFixedSize(42, 42)
        mark.setAlignment(Qt.AlignCenter)
        logo = logo_path()
        if logo:
            mark.setPixmap(circular_pixmap(logo, 42))
        else:
            mark.setObjectName("sidebarMark")
            mark.setText("D")
        brand_row.addWidget(mark)
        brand_text = QVBoxLayout()
        brand_text.setSpacing(0)
        brand = QLabel("DOCARCHIVE")
        brand.setObjectName("brand")
        brand_caption = QLabel("Document Archiving Suite")
        brand_caption.setObjectName("brandCaption")
        brand_text.addWidget(brand)
        brand_text.addWidget(brand_caption)
        brand_row.addLayout(brand_text)
        brand_row.addStretch()
        side.addLayout(brand_row)
        side.addSpacing(30)

        self.archive_nav = QPushButton("🗂   New Archive")
        self.search_nav = QPushButton("🔍   Search Archive")
        nav_list = [self.archive_nav, self.search_nav]
        for button in nav_list:
            button.setObjectName("navButton")
            button.setMinimumHeight(46)
            button.setCursor(Qt.PointingHandCursor)
            button.setLayoutDirection(Qt.LeftToRight)
            side.addWidget(button)
        side.addStretch()

        divider = QFrame()
        divider.setObjectName("sidebarDivider")
        divider.setFixedHeight(1)
        side.addWidget(divider)
        side.addSpacing(14)

        user_row = QHBoxLayout()
        user_row.setSpacing(10)
        initial = (self.client.username or "?")[:1].upper()
        avatar = QLabel(initial)
        avatar.setObjectName("avatarBadge")
        avatar.setFixedSize(36, 36)
        avatar.setAlignment(Qt.AlignCenter)
        user_row.addWidget(avatar)
        user_text = QVBoxLayout()
        user_text.setSpacing(0)
        user_name = QLabel(self.client.username or "—")
        user_name.setObjectName("userName")
        user_state = QLabel("● Online")
        user_state.setObjectName("userState")
        user_text.addWidget(user_name)
        user_text.addWidget(user_state)
        user_row.addLayout(user_text)
        user_row.addStretch()
        side.addLayout(user_row)
        side.addSpacing(10)

        logout = QPushButton("🚪   Sign Out")
        logout.setObjectName("logoutButton")
        logout.setMinimumHeight(40)
        logout.setCursor(Qt.PointingHandCursor)
        logout.clicked.connect(self.close)
        side.addWidget(logout)

        return sidebar

    def build_header(self):
        header = QHBoxLayout()
        header.setSpacing(14)
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        self.page_title = QLabel("Archive Document")
        self.page_title.setObjectName("pageTitle")
        self.page_subtitle = QLabel("Scan a document or upload a PDF file for digital archiving")
        self.page_subtitle.setObjectName("pageSubtitle")
        title_box.addWidget(self.page_title)
        title_box.addWidget(self.page_subtitle)
        header.addLayout(title_box)
        header.addStretch()

        server_chip = QLabel(f"🖥  {self.client.server_url}")
        server_chip.setObjectName("chip")
        header.addWidget(server_chip, 0, Qt.AlignTop)

        self.status_chip = QLabel("Ready")
        self.status_chip.setObjectName("statusChip")
        self.status_chip.setProperty("state", "neutral")
        header.addWidget(self.status_chip, 0, Qt.AlignTop)
        return header

    def switch_page(self, index):
        self.pages.setCurrentIndex(index)
        self.set_active_nav(self.nav_buttons[index])
        title, subtitle = self.page_meta[index]
        self.page_title.setText(title)
        self.page_subtitle.setText(subtitle)

    def set_active_nav(self, active_button):
        for button in self.nav_buttons:
            button.setObjectName("navActive" if button is active_button else "navButton")
            button.setStyleSheet(button.styleSheet())
            button.style().unpolish(button)
            button.style().polish(button)

    def card(self):
        frame = QFrame()
        frame.setObjectName("card")
        apply_shadow(frame, blur=32, y_offset=12, opacity=28)
        return frame

    def section_title(self, text):
        label = QLabel(text)
        label.setObjectName("sectionTitle")
        return label

    def divider(self):
        line = QFrame()
        line.setObjectName("divider")
        line.setFixedHeight(1)
        return line

    def build_archive_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        card = self.card()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(34, 30, 34, 30)
        card_layout.setSpacing(14)

        card_layout.addWidget(self.section_title("1 · Document Details"))
        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(10)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        self.number = field("e.g. 2026/DOC/001")
        self.date = field("YYYY-MM-DD")
        self.title = field("Document Subject or Title")
        for editor in (self.number, self.date, self.title):
            editor.setMinimumHeight(44)
        self.notes = QTextEdit()
        self.notes.setPlaceholderText("Optional notes or summary description")
        self.notes.setMinimumHeight(78)
        self.notes.setMaximumHeight(96)

        subject_label = field_label("Subject / Title *")
        subject_label.setMinimumHeight(22)
        grid.addWidget(subject_label, 0, 0, 1, 2)
        grid.addWidget(self.title, 1, 0, 1, 2)

        number_label = field_label("Document Number *")
        date_label = field_label("Date *")
        number_label.setMinimumHeight(22)
        date_label.setMinimumHeight(22)
        grid.addWidget(number_label, 2, 0)
        grid.addWidget(date_label, 2, 1)
        grid.addWidget(self.number, 3, 0)
        grid.addWidget(self.date, 3, 1)

        notes_label = field_label("Notes")
        notes_label.setMinimumHeight(22)
        grid.addWidget(notes_label, 4, 0, 1, 2)
        grid.addWidget(self.notes, 5, 0, 1, 2)
        card_layout.addLayout(grid)

        card_layout.addSpacing(6)
        card_layout.addWidget(self.divider())
        card_layout.addSpacing(6)

        card_layout.addWidget(self.section_title("2 · Archiving Options"))
        options_row = QHBoxLayout()
        options_row.setSpacing(10)

        type_box = QVBoxLayout()
        type_box.setSpacing(6)
        type_box.addWidget(field_label("Document Type"))
        type_row = QHBoxLayout()
        type_row.setSpacing(10)
        self.document_type_combo = QComboBox()
        self.document_type_combo.setMinimumHeight(42)
        self.document_type_combo.addItem("Loading document types...", None)
        type_row.addWidget(self.document_type_combo, 1)
        type_refresh = QPushButton("↻  Refresh")
        type_refresh.setObjectName("ghostButton")
        type_refresh.setMinimumHeight(42)
        type_refresh.setCursor(Qt.PointingHandCursor)
        type_refresh.clicked.connect(self.load_document_types)
        type_row.addWidget(type_refresh)
        type_box.addLayout(type_row)
        options_row.addLayout(type_box, 1)

        device_box = QVBoxLayout()
        device_box.setSpacing(6)
        device_box.addWidget(field_label("Scanner Device"))
        device_row = QHBoxLayout()
        device_row.setSpacing(10)
        self.device_combo = QComboBox()
        self.device_combo.setMinimumHeight(42)
        device_row.addWidget(self.device_combo, 1)
        refresh = QPushButton("↻  Refresh")
        refresh.setObjectName("ghostButton")
        refresh.setMinimumHeight(42)
        refresh.setCursor(Qt.PointingHandCursor)
        refresh.clicked.connect(self.refresh_devices)
        device_row.addWidget(refresh)
        device_box.addLayout(device_row)
        options_row.addLayout(device_box, 1)

        card_layout.addLayout(options_row)

        self.file_label = QLabel("No PDF file selected")
        self.file_label.setObjectName("filePill")
        card_layout.addWidget(self.file_label)

        card_layout.addSpacing(4)
        card_layout.addWidget(self.divider())
        card_layout.addSpacing(10)

        actions = QHBoxLayout()
        actions.setSpacing(10)
        self.pdf_button = QPushButton("📄  Choose && Upload PDF")
        self.pdf_button.setObjectName("primaryButton")
        self.scan_button = QPushButton("🖨   Scan && Archive")
        self.scan_button.setObjectName("successButton")
        for button in (self.pdf_button, self.scan_button):
            button.setMinimumHeight(44)
            button.setCursor(Qt.PointingHandCursor)
        self.scan_button.clicked.connect(self.scan_and_archive)
        self.pdf_button.clicked.connect(self.choose_and_archive_pdf)
        actions.addStretch()
        actions.addWidget(self.pdf_button)
        actions.addWidget(self.scan_button)
        card_layout.addLayout(actions)

        layout.addWidget(card)
        layout.addStretch()
        return page

    def build_search_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        card = self.card()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(34, 30, 34, 30)
        card_layout.setSpacing(14)

        card_layout.addWidget(self.section_title("Search by document number, subject, or title keyword"))
        row = QHBoxLayout()
        row.setSpacing(10)
        self.query = field("🔍  Type document number or keyword...")
        self.query.returnPressed.connect(self.search)
        button = QPushButton("Search")
        button.setObjectName("primaryButton")
        button.setMinimumHeight(42)
        button.setMinimumWidth(110)
        button.setCursor(Qt.PointingHandCursor)
        button.clicked.connect(self.search)
        row.addWidget(self.query, 1)
        row.addWidget(button)
        card_layout.addLayout(row)

        self.results_caption = QLabel("No results yet")
        self.results_caption.setObjectName("muted")
        card_layout.addWidget(self.results_caption)

        hint = QLabel("💡  Double-click any row to download and open the document")
        hint.setObjectName("muted")
        card_layout.addWidget(hint)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Document #", "Subject", "Description"])
        self.table.setColumnWidth(0, 180)
        self.table.setColumnWidth(1, 300)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.cellDoubleClicked.connect(self.open_result)
        card_layout.addWidget(self.table)
        layout.addWidget(card)
        return page

    def set_status(self, text, kind="neutral"):
        self.status_chip.setText(text)
        self.status_chip.setProperty("state", kind)
        self.status_chip.style().unpolish(self.status_chip)
        self.status_chip.style().polish(self.status_chip)

    def set_busy(self, busy, text):
        self.scan_button.setEnabled(not busy)
        self.pdf_button.setEnabled(not busy)
        self.set_status(text, "busy" if busy else "neutral")

    def run_async(self, function, success, failure):
        worker = Worker(function, parent=self)
        worker.finished.connect(success)
        worker.failed.connect(failure)
        worker.finished.connect(worker.deleteLater)
        worker.failed.connect(worker.deleteLater)
        worker.start()

    def refresh_devices(self):
        self.device_combo.clear()
        self.device_combo.addItem("Detecting scanner devices...")
        def list_devices():
            result = subprocess.run(
                [naps2_path(), "--listdevices"],
                capture_output=True, text=True, timeout=30,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            output = (result.stdout or result.stderr or "").strip()
            devices = [line.strip() for line in output.splitlines() if line.strip()]
            if result.returncode != 0 or not devices:
                raise RuntimeError(output or "No scanner devices detected.")
            return devices
        self.run_async(list_devices, self.devices_loaded, self.devices_failed)

    def load_document_types(self):
        self.set_status("Loading document types...", "busy")
        self.run_async(self.client.document_types, self.document_types_loaded, self.document_types_failed)

    def document_types_loaded(self, types):
        if not types:
            self.document_types_failed(
                "No document types assigned to your account.\n\n"
                "Please contact your administrator to ensure:\n"
                "1. An archiving role exists with document type permissions.\n"
                "2. Your user group is associated with that role."
            )
            return
        self.document_type_combo.clear()
        selected_index = 0
        for index, item in enumerate(types):
            type_id = int(item["id"])
            self.document_type_combo.addItem(f"{item['label']}  (ID {type_id})", type_id)
            if type_id == int(self.client.document_type_id):
                selected_index = index
        self.document_type_combo.setCurrentIndex(selected_index)
        self.client.document_type_id = int(self.document_type_combo.currentData())
        self.set_status(f"Document Type: {self.document_type_combo.currentText()}", "neutral")

    def document_types_failed(self, message):
        self.document_type_combo.clear()
        self.document_type_combo.addItem("Could not load types — click Refresh", None)
        self.set_status("Failed to load document types", "error")
        QMessageBox.warning(self, "Document Types", message)

    def devices_loaded(self, devices):
        self.devices = devices
        self.device_combo.clear()
        self.device_combo.addItems(devices)
        self.set_status(f"Found {len(devices)} scanner device(s)", "success")

    def devices_failed(self, message):
        self.devices = []
        self.device_combo.clear()
        self.device_combo.addItem("No scanner device detected")
        self.set_status("No scanner devices found", "error")

    def selected_document_type(self):
        value = self.document_type_combo.currentData()
        if value is None:
            raise RuntimeError("Please select a document type first.")
        return int(value)

    def metadata(self):
        number, title, date = self.number.text().strip(), self.title.text().strip(), self.date.text().strip()
        if not number or not title or not date:
            raise RuntimeError("Please enter document number, subject, and date.")
        return number, title, date, self.notes.toPlainText().strip()

    def choose_and_archive_pdf(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select PDF Document", "", "PDF Files (*.pdf)")
        if not path:
            return
        self.selected_pdf = Path(path)
        self.file_label.setText(f"📎  Selected file: {self.selected_pdf.name}")
        try:
            document_type_id = self.selected_document_type()
            number, title, date, notes = self.metadata()
        except RuntimeError as error:
            QMessageBox.warning(self, "Incomplete Data", str(error))
            return
        self.set_busy(True, "Uploading PDF...")
        self.run_async(
            lambda: self.client.archive(self.selected_pdf, number, title, date, notes, document_type_id),
            lambda result: self.archive_success(result, "PDF document archived successfully!"),
            self.archive_failed,
        )

    def scan_and_archive(self):
        if not self.devices:
            QMessageBox.warning(self, "Scanner Device", "Please select an available scanner device first.")
            return
        try:
            document_type_id = self.selected_document_type()
            number, title, date, notes = self.metadata()
        except RuntimeError as error:
            QMessageBox.warning(self, "Incomplete Data", str(error))
            return
        device = self.device_combo.currentText()
        self.set_busy(True, "Scanning in progress...")
        def scan_upload():
            temp_path = None
            try:
                with tempfile.NamedTemporaryFile(prefix="archive_scan_", suffix=".pdf", delete=False) as temp:
                    temp_path = Path(temp.name)
                result = subprocess.run(
                    [naps2_path(), "--device", device, "-o", str(temp_path), "--force"],
                    capture_output=True, text=True, timeout=180,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
                if result.returncode != 0 or not temp_path.exists() or temp_path.stat().st_size == 0:
                    raise RuntimeError(result.stderr or result.stdout or "Scanner operation failed.")
                return self.client.archive(temp_path, number, title, date, notes, document_type_id)
            finally:
                if temp_path and temp_path.exists():
                    temp_path.unlink(missing_ok=True)
        self.run_async(scan_upload, lambda result: self.archive_success(result, "Scan completed and archived successfully!"), self.archive_failed)

    def archive_success(self, result, message):
        self.set_busy(False, "Ready")
        self.set_status(message, "success")
        self.number.clear(); self.title.clear(); self.date.clear(); self.notes.clear()
        self.selected_pdf = None; self.file_label.setText("No PDF file selected")
        QMessageBox.information(self, "Success", message)

    def archive_failed(self, message):
        self.set_busy(False, "Operation failed")
        self.set_status("Operation failed", "error")
        QMessageBox.critical(self, "Error", message)

    def search(self):
        query = self.query.text().strip()
        if not query:
            return
        self.set_status("Searching...", "busy")
        self.run_async(
            lambda: self.client.search(query),
            self.show_results,
            lambda msg: (self.set_status("Search failed", "error"), QMessageBox.critical(self, "Search", msg))
        )

    def show_results(self, items):
        self.table.setRowCount(0)
        for raw in items:
            item = self.client._unwrap_document(raw)
            row = self.table.rowCount()
            self.table.insertRow(row)
            label = str(item.get("label", ""))
            if " - " in label:
                book_number, subject = label.split(" - ", 1)
            else:
                book_number, subject = label, label
            values = [book_number, subject, item.get("description", "")]
            for col, value in enumerate(values):
                cell = QTableWidgetItem(str(value))
                if col == 0:
                    cell.setData(Qt.UserRole, item.get("id"))
                self.table.setItem(row, col, cell)
        self.results_caption.setText(f"Found {len(items)} matching document(s)" if items else "No matching documents found")
        self.set_status(f"Found {len(items)} document(s)", "success" if items else "neutral")

    def open_result(self, row, _column):
        id_item = self.table.item(row, 0)
        document_id = id_item.data(Qt.UserRole) if id_item else None
        if document_id is None:
            QMessageBox.warning(self, "Open Document", "Unable to determine document ID.")
            return
        self.set_status("Downloading document...", "busy")
        self.run_async(
            lambda: self.client.download_document(document_id),
            self.open_local_document,
            self.open_document_failed,
        )

    def open_local_document(self, local_path):
        self.set_status("Document downloaded", "success")
        try:
            if hasattr(os, "startfile"):
                os.startfile(local_path)
            else:
                webbrowser.open(Path(local_path).as_uri())
        except Exception as error:
            QMessageBox.critical(self, "Open Document", f"File downloaded, but could not be opened automatically:\n{local_path}\n{error}")

    def open_document_failed(self, message):
        self.set_status("Failed to download document", "error")
        QMessageBox.critical(self, "Open Document", message)


def main():
    app = QApplication(sys.argv)
    app.setLayoutDirection(Qt.LeftToRight)
    app.setStyleSheet(STYLESHEET)
    logo = logo_path()
    if logo:
        app.setWindowIcon(QIcon(str(logo)))
    settings = load_settings()
    client = ArchiveClient(settings.get("server_url", DEFAULT_SERVER), int(settings.get("document_type_id", DOCUMENT_TYPE_ID)))
    login = LoginWindow(client)
    def open_main(authed_client):
        window = MainWindow(authed_client)
        window.show()
        app.main_window = window
    login.logged_in.connect(open_main)
    login.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
