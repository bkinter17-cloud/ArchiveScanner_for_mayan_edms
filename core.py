import json
import os
import sys
import tempfile
from pathlib import Path

import requests
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (
    QFrame, QGraphicsDropShadowEffect, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QStyle, QStyleOption, QVBoxLayout, QWidget
)

APP_NAME = "ArchiveScanner"
DOCUMENT_TYPE_ID = int(os.getenv("MAYAN_DOCUMENT_TYPE_ID", "4"))
DEFAULT_SERVER = os.getenv("MAYAN_URL", "http://192.168.234.129:8000")

# ---------------------------------------------------------------------------
# Design tokens — visual identity
# ---------------------------------------------------------------------------
BG = "#f8fafc"
SURFACE = "#ffffff"
BORDER = "#e2e8f0"
TEXT = "#0f172a"
MUTED = "#64748b"
SIDEBAR_TOP = "#0f172a"
SIDEBAR_BOTTOM = "#1e293b"
ACCENT = "#4f46e5"
ACCENT_DARK = "#4338ca"
ACCENT_LIGHT = "#eef2ff"
ACCENT_GLOW = "#c7d2fe"
MINT = "#06b6d4"
SUCCESS = "#059669"
SUCCESS_DARK = "#047857"
SUCCESS_LIGHT = "#ecfdf5"
DANGER = "#dc2626"
DANGER_LIGHT = "#fef2f2"
FONT_STACK = "'Segoe UI', 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI Emoji', system-ui, sans-serif"


def application_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def settings_path(write=False):
    beside_exe = application_dir() / "settings.json"
    if not write:
        if beside_exe.exists():
            return beside_exe
        app_data_file = Path(os.environ.get("APPDATA", Path.home())) / "ArchiveScanner" / "settings.json"
        if app_data_file.exists():
            return app_data_file
        return beside_exe

    # For writing: test if beside_exe is writable
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

    # Fallback to user APPDATA folder
    app_data_dir = Path(os.environ.get("APPDATA", Path.home())) / "ArchiveScanner"
    app_data_dir.mkdir(parents=True, exist_ok=True)
    return app_data_dir / "settings.json"


def load_settings():
    beside_exe = application_dir() / "settings.json"
    if beside_exe.exists():
        try:
            return json.loads(beside_exe.read_text(encoding="utf-8"))
        except Exception:
            pass

    app_data_file = Path(os.environ.get("APPDATA", Path.home())) / "ArchiveScanner" / "settings.json"
    if app_data_file.exists():
        try:
            return json.loads(app_data_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    return {"server_url": DEFAULT_SERVER, "document_type_id": DOCUMENT_TYPE_ID}


def save_settings(server_url, document_type_id=DOCUMENT_TYPE_ID):
    data = {"server_url": server_url.rstrip("/"), "document_type_id": int(document_type_id)}
    target = settings_path(write=True)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data


def naps2_path():
    override = os.getenv("NAPS2_CONSOLE", "").strip()
    if override:
        return override
    candidates = []
    if getattr(sys, "frozen", False):
        candidates.append(Path(sys._MEIPASS) / "NAPS2" / "NAPS2.Console.exe")
    candidates += [
        application_dir() / "NAPS2" / "NAPS2.Console.exe",
        Path(os.environ.get("PROGRAMFILES", "C:/Program Files")) / "NAPS2" / "NAPS2.Console.exe",
        Path(os.environ.get("PROGRAMFILES(X86)", "C:/Program Files (x86)")) / "NAPS2" / "NAPS2.Console.exe",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return "naps2.console"


def logo_path():
    """Locate the bundled logo, both when run from source and when
    frozen by PyInstaller (assets are unpacked to sys._MEIPASS)."""
    candidates = []
    if getattr(sys, "frozen", False):
        candidates.append(Path(sys._MEIPASS) / "assets" / "logo.png")
    candidates += [
        application_dir() / "assets" / "logo.png",
        Path(__file__).resolve().parent / "assets" / "logo.png",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def circular_pixmap(source_path, size, ring=True, ring_color=QColor(255, 255, 255, 110)):
    source = QPixmap(str(source_path))
    if source.isNull():
        return QPixmap()
    scaled = source.scaled(size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
    x, y = (scaled.width() - size) // 2, (scaled.height() - size) // 2
    cropped = scaled.copy(x, y, size, size)

    result = QPixmap(size, size)
    result.fill(Qt.transparent)
    painter = QPainter(result)
    painter.setRenderHint(QPainter.Antialiasing)
    clip = QPainterPath()
    clip.addEllipse(0, 0, size, size)
    painter.setClipPath(clip)
    painter.drawPixmap(0, 0, cropped)
    if ring:
        painter.setClipping(False)
        pen = QPen(ring_color)
        pen.setWidthF(1.6)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(1, 1, size - 2, size - 2)
    painter.end()
    return result


class BrandPanel(QFrame):
    """The dark login/sidebar panel — paints its own gradient plus a watermark logo."""

    def __init__(self, watermark_size_ratio=1.0, corner="bottom-left", opacity=0.07, parent=None):
        super().__init__(parent)
        self._watermark = None
        logo = logo_path()
        if logo:
            source = QPixmap(str(logo))
            if not source.isNull():
                self._watermark = source
        self._ratio = watermark_size_ratio
        self._corner = corner
        self._opacity = opacity

    def paintEvent(self, event):
        opt = QStyleOption()
        opt.initFrom(self)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        self.style().drawPrimitive(QStyle.PE_Widget, opt, painter, self)
        if self._watermark is not None and self.height() > 0:
            target = int(self.height() * self._ratio)
            scaled = self._watermark.scaled(target, target, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            bleed_x, bleed_y = int(scaled.width() * 0.32), int(scaled.height() * 0.32)
            if self._corner == "bottom-right":
                x, y = self.width() - scaled.width() + bleed_x, self.height() - scaled.height() + bleed_y
            else:
                x, y = -bleed_x, self.height() - scaled.height() + bleed_y
            painter.setOpacity(self._opacity)
            painter.drawPixmap(x, y, scaled)
        painter.end()


class ArchiveClient:
    def __init__(self, server_url, document_type_id):
        self.server_url = server_url.rstrip("/")
        self.document_type_id = document_type_id
        self.session = requests.Session()
        self.token = ""
        self.username = ""
        self.user_id = None

    @property
    def headers(self):
        return {"Authorization": f"Token {self.token}", "Accept": "application/json"}

    def login(self, username, password):
        try:
            response = self.session.post(
                f"{self.server_url}/api/v4/auth/token/obtain/",
                params={"format": "json"},
                data={"username": username, "password": password},
                headers={"Accept": "application/json"},
                timeout=(5, 15),
                allow_redirects=False,
            )
        except requests.exceptions.ConnectTimeout:
            raise RuntimeError(
                f"Connection timed out after 5 seconds to:\n{self.server_url}\n"
                "Please verify that the server address, port, and network connection are operational."
            )
        except requests.exceptions.ReadTimeout:
            raise RuntimeError(
                "Server connected but did not respond within 15 seconds.\n"
                "Please check the server load or Mayan EDMS service status."
            )
        except requests.exceptions.ConnectionError as error:
            raise RuntimeError(
                f"Failed to connect to the archive server:\n{self.server_url}\n{error}"
            )
        if response.status_code not in (200, 201):
            try:
                detail = response.json()
            except ValueError:
                detail = response.text[:500]
            raise RuntimeError(f"Authentication failed ({response.status_code})\n{detail}")
        data = response.json()
        self.token = data.get("token") or data.get("key") or data.get("auth_token", "")
        if not self.token:
            raise RuntimeError(f"Server did not return a valid auth token:\n{data}")
        self.username = username
        self._load_current_user()

    def _load_current_user(self):
        try:
            response = self.session.get(
                f"{self.server_url}/api/v4/users/current/",
                headers=self.headers, timeout=(5, 15),
            )
            if response.status_code == 200:
                data = response.json()
                info = self._unwrap_document(data) if isinstance(data, dict) else {}
                info = info or (data if isinstance(data, dict) else {})
                if info.get("id") is not None:
                    self.user_id = info.get("id")
                    return
        except (requests.exceptions.RequestException, ValueError):
            pass

        try:
            response = self.session.get(
                f"{self.server_url}/api/v4/users/",
                headers=self.headers, params={"page_size": 200}, timeout=(5, 15),
            )
            if response.status_code != 200:
                return
            for raw in response.json().get("results", []):
                item = raw.get("entry", raw) if isinstance(raw, dict) else {}
                if item.get("username") == self.username:
                    self.user_id = item.get("id")
                    return
        except (requests.exceptions.RequestException, ValueError):
            return

    def document_types(self):
        response = self.session.get(
            f"{self.server_url}/api/v4/document_types/",
            headers=self.headers, params={"page_size": 100}, timeout=(5, 15),
        )
        if response.status_code != 200:
            raise RuntimeError(f"Failed to fetch document types ({response.status_code})\n{response.text[:500]}")
        data = response.json()
        items = data.get("results") or data.get("list", {}).get("results") or data.get("list", {}).get("entries") or []
        types = []
        for raw in items:
            item = raw.get("entry", raw) if isinstance(raw, dict) else {}
            if item.get("id") is not None:
                types.append({"id": item["id"], "label": item.get("label", str(item["id"]))})
        return types

    def archive(self, pdf_path, number, title, date, notes="", document_type_id=None):
        """Two-step Mayan EDMS v4 document creation and file upload."""
        selected_type_id = int(document_type_id or self.document_type_id)
        payload = {
            "document_type_id": selected_type_id,
            "label": f"{number} - {title}",
            "description": f"Date: {date}\nNotes: {notes}".strip(),
        }
        create_response = self.session.post(
            f"{self.server_url}/api/v4/documents/",
            headers=self.headers,
            data=payload,
            timeout=(5, 30),
        )
        if create_response.status_code not in (200, 201):
            try:
                detail = create_response.json()
            except ValueError:
                detail = create_response.text[:1000]
            raise RuntimeError(
                f"Failed to create document record ({create_response.status_code})\n{detail}\n"
                f"Document Type ID: {selected_type_id}"
            )

        result = create_response.json() if create_response.content else {}
        document_obj = self._unwrap_document(result)
        document_id = (
            document_obj.get("id")
            or result.get("document_id")
            or result.get("document_id_id")
        )
        if document_id is None:
            document_url = document_obj.get("url") or result.get("document_url")
            if document_url:
                try:
                    document_id = int(str(document_url).rstrip("/").split("/")[-1])
                except (TypeError, ValueError):
                    document_id = None
        if document_id is None:
            raise RuntimeError(f"Unexpected server response; document ID missing:\n{result}")

        # Verify document existence
        verify_response = self.session.get(
            f"{self.server_url}/api/v4/documents/{int(document_id)}/",
            headers=self.headers,
            timeout=(5, 30),
        )
        if verify_response.status_code != 200:
            raise RuntimeError(
                f"Document record was created but could not be verified (HTTP {verify_response.status_code}).\n"
                f"Document ID: {document_id}"
            )

        # Upload the file to /api/v4/documents/{id}/files/
        with Path(pdf_path).open("rb") as stream:
            file_response = self.session.post(
                f"{self.server_url}/api/v4/documents/{int(document_id)}/files/",
                headers=self.headers,
                data={"action_name": "replace"},
                files={"file_new": (Path(pdf_path).name, stream, "application/pdf")},
                timeout=(5, 180),
            )
        if file_response.status_code not in (200, 201, 202):
            try:
                detail = file_response.json()
            except ValueError:
                detail = file_response.text[:1000]
            raise RuntimeError(
                f"Document record #{document_id} created, but file upload failed ({file_response.status_code})\n{detail}"
            )
        if isinstance(result, dict) and file_response.content:
            try:
                result["file_upload"] = file_response.json()
            except ValueError:
                pass
        return result

    def download_document(self, document_id):
        document_id = int(document_id)
        base = f"{self.server_url}/api/v4/documents/{document_id}"
        candidates = []

        # 1. Document details
        detail_response = self.session.get(
            f"{base}/", headers=self.headers, timeout=(5, 30)
        )
        if detail_response.status_code == 200:
            detail_data = detail_response.json()
            detail = detail_data.get("entry", detail_data) if isinstance(detail_data, dict) else {}
            file_latest = detail.get("file_latest") or {}
            if isinstance(file_latest, dict):
                if file_latest.get("download_url"):
                    candidates.append(file_latest["download_url"])
                file_id = file_latest.get("id")
                if file_id is not None:
                    candidates.append(f"{base}/files/{file_id}/download/")
                for key in ("download_url", "document_file_url", "file_url"):
                    val = file_latest.get(key)
                    if val and val not in candidates:
                        candidates.append(val)
            for key in ("download_url", "document_file_url", "file_url"):
                val = detail.get(key)
                if val and val not in candidates:
                    candidates.append(val)

            version_active = detail.get("version_active") or {}
            if isinstance(version_active, dict):
                v_id = version_active.get("id")
                if version_active.get("download_url"):
                    candidates.append(version_active["download_url"])
                if v_id is not None:
                    candidates.append(f"{base}/versions/{v_id}/download/")
                if version_active.get("export_url"):
                    candidates.append(version_active["export_url"])
        else:
            detail = {}

        # 2. Files list endpoint
        files_url = detail.get("files_url") or detail.get("document_files_url") or f"{base}/files/"
        try:
            files_response = self.session.get(files_url, headers=self.headers, timeout=(5, 30))
            if files_response.status_code == 200:
                files_data = files_response.json()
                results = (
                    files_data.get("results")
                    or files_data.get("objects")
                    or files_data.get("items")
                    or []
                )
                if isinstance(results, list):
                    for f_entry in reversed(results):
                        f_item = f_entry.get("entry", f_entry) if isinstance(f_entry, dict) else {}
                        if f_item.get("download_url") and f_item["download_url"] not in candidates:
                            candidates.append(f_item["download_url"])
                        f_id = f_item.get("id")
                        if f_id is not None:
                            f_url = f"{base}/files/{f_id}/download/"
                            if f_url not in candidates:
                                candidates.append(f_url)
        except Exception:
            pass

        # 3. Fallbacks
        for fallback in (f"{base}/download/", f"{base}/file/"):
            if fallback not in candidates:
                candidates.append(fallback)

        last_status = None
        last_body = ""
        for download_url in candidates:
            if download_url.startswith("/"):
                download_url = f"{self.server_url}{download_url}"
            elif not download_url.startswith("http"):
                download_url = f"{self.server_url}/{download_url.lstrip('/')}"

            try:
                response = self.session.get(
                    download_url, headers=self.headers, timeout=(5, 180), stream=True,
                )
            except Exception as e:
                last_body = str(e)
                continue

            last_status = response.status_code
            if response.status_code != 200:
                try:
                    last_body = response.text[:500]
                except Exception:
                    pass
                continue

            content_type = response.headers.get("content-type", "").lower()
            if "application/json" in content_type or "text/html" in content_type:
                last_body = f"Skipping non-binary metadata response ({content_type}) from: {download_url}"
                continue

            suffix = ".pdf"
            cd = response.headers.get("content-disposition", "")
            if "filename=" in cd:
                fname = cd.split("filename=")[-1].strip('"\' ;')
                ext = Path(fname).suffix.lower()
                if ext in (".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif", ".txt", ".docx", ".xlsx"):
                    suffix = ext
            elif "image/jpeg" in content_type:
                suffix = ".jpg"
            elif "image/png" in content_type:
                suffix = ".png"
            elif "image/tiff" in content_type:
                suffix = ".tiff"

            first_chunk = True
            is_valid_binary = True
            with tempfile.NamedTemporaryFile(prefix=f"archive_doc_{document_id}_", suffix=suffix, delete=False) as output:
                for chunk in response.iter_content(chunk_size=1024 * 256):
                    if not chunk:
                        continue
                    if first_chunk:
                        first_chunk = False
                        stripped = chunk.lstrip()
                        if stripped.startswith((b"{", b"[", b"<!DOCTYPE", b"<html", b"<?xml")):
                            is_valid_binary = False
                            break
                    output.write(chunk)
                local_path = Path(output.name)

            if is_valid_binary and local_path.exists() and local_path.stat().st_size > 0:
                return str(local_path)

            if local_path.exists():
                local_path.unlink(missing_ok=True)

        raise RuntimeError(
            f"Could not download document file. (HTTP status: {last_status}).\n{last_body}"
        )

    @staticmethod
    def _unwrap_document(raw):
        if not isinstance(raw, dict):
            return {}
        for key in ("document", "object", "entry", "result"):
            nested = raw.get(key)
            if isinstance(nested, dict) and ("label" in nested or "id" in nested):
                return nested
        return raw

    @staticmethod
    def _normalise_digits(value):
        table = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
        return str(value).translate(table).strip().casefold()

    def search(self, query):
        query = str(query).strip()
        if not query:
            return []
        response = self.session.get(
            f"{self.server_url}/api/v4/search/",
            headers=self.headers, params={"q": query}, timeout=60,
        )
        if response.status_code != 200:
            response = self.session.get(
                f"{self.server_url}/api/v4/documents/",
                headers=self.headers, params={"page_size": 100}, timeout=60,
            )
        if response.status_code != 200:
            raise RuntimeError(f"Search request failed ({response.status_code})\n{response.text[:500]}")
        data = response.json()
        items = data.get("results") or data.get("list", {}).get("results", []) or []
        needle = self._normalise_digits(query)
        numeric_query = needle.isdigit()
        filtered = []
        for raw in items:
            item = self._unwrap_document(raw)
            label = str(item.get("label", "")).strip()
            description = str(item.get("description", "")).strip()
            number = label.split(" - ", 1)[0].strip() if " - " in label else label
            if numeric_query:
                matches = self._normalise_digits(number) == needle
            else:
                searchable = self._normalise_digits(f"{label} {description}")
                matches = needle in searchable
            if matches:
                filtered.append(item)
        return filtered


class Worker(QThread):
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, function, *args, parent=None):
        super().__init__(parent)
        self.function, self.args = function, args

    def run(self):
        try:
            self.finished.emit(self.function(*self.args))
        except Exception as error:
            self.failed.emit(str(error))


def apply_shadow(widget, blur=36, y_offset=14, color=None, opacity=40):
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setOffset(0, y_offset)
    effect.setColor(color or QColor(17, 24, 39, opacity))
    widget.setGraphicsEffect(effect)


def field(placeholder, password=False):
    box = QLineEdit()
    box.setPlaceholderText(placeholder)
    box.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    box.setMinimumHeight(42)
    if password:
        box.setEchoMode(QLineEdit.Password)
    return box


def field_label(text, word_wrap=False):
    label = QLabel(text)
    label.setObjectName("fieldLabel")
    label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    label.setWordWrap(word_wrap)
    return label


class LoginWindow(QWidget):
    logged_in = Signal(object)

    def __init__(self, client, window_title="Sign In | DocArchive Scanner",
                 brand_title="DocArchive",
                 brand_subtitle="Unified digital document scanning and archiving platform.",
                 brand_features=(
                     "Direct scanner capture from Twain / WIA hardware",
                     "Instant indexing and archiving to Mayan EDMS",
                     "Fast full-text document search and retrieval",
                 ),
                 login_caption="Enter your credentials to access the archive"):
        super().__init__()
        self.client = client
        self._brand_title = brand_title
        self._brand_subtitle = brand_subtitle
        self._brand_features = brand_features
        self._login_caption = login_caption
        self.setWindowTitle(window_title)
        self.setMinimumSize(800, 560)
        self.resize(960, 640)
        self.setLayoutDirection(Qt.LeftToRight)
        self.build_ui()

    def build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self.build_brand_panel())
        root.addWidget(self.build_form_panel(), 1)
        self.username.setFocus()

    def build_brand_panel(self):
        panel = BrandPanel(watermark_size_ratio=0.62, corner="bottom-left", opacity=0.08)
        panel.setObjectName("brandPanel")
        panel.setFixedWidth(360)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(48, 56, 48, 48)
        layout.addStretch(1)

        mark = QLabel()
        mark.setFixedSize(84, 84)
        mark.setAlignment(Qt.AlignCenter)
        logo = logo_path()
        if logo:
            mark.setPixmap(circular_pixmap(logo, 84))
        else:
            mark.setObjectName("brandMark")
            mark.setText("D")
        layout.addWidget(mark, 0, Qt.AlignLeft)
        layout.addSpacing(22)

        title = QLabel(self._brand_title)
        title.setObjectName("brandTitle")
        title.setWordWrap(True)
        layout.addWidget(title)

        subtitle = QLabel(self._brand_subtitle)
        subtitle.setObjectName("brandSubtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)
        layout.addSpacing(34)

        for line in self._brand_features:
            row = QHBoxLayout()
            row.setSpacing(10)
            dot = QLabel("●")
            dot.setObjectName("brandBullet")
            dot.setFixedWidth(14)
            text = QLabel(line)
            text.setObjectName("brandFeature")
            text.setWordWrap(True)
            row.addWidget(dot, 0, Qt.AlignTop)
            row.addWidget(text, 1)
            layout.addLayout(row)
            layout.addSpacing(10)

        layout.addStretch(2)
        return panel

    def build_form_panel(self):
        panel = QFrame()
        panel.setObjectName("loginPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(60, 45, 60, 35)
        layout.addStretch(1)

        heading = QLabel("Sign In")
        heading.setObjectName("loginHeading")
        layout.addWidget(heading)
        caption = QLabel(self._login_caption)
        caption.setObjectName("muted")
        layout.addWidget(caption)
        layout.addSpacing(20)

        layout.addWidget(field_label("Archive Server URL"))
        self.server_input = field("e.g. http://192.168.1.100:8000")
        self.server_input.setText(self.client.server_url or DEFAULT_SERVER)
        self.server_input.setLayoutDirection(Qt.LeftToRight)
        self.server_input.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        layout.addWidget(self.server_input)
        layout.addSpacing(14)

        layout.addWidget(field_label("Username"))
        self.username = field("Enter username")
        layout.addWidget(self.username)
        layout.addSpacing(14)

        layout.addWidget(field_label("Password"))
        self.password = field("••••••••", password=True)
        layout.addWidget(self.password)
        layout.addSpacing(16)

        self.status = QLabel(" ")
        self.status.setObjectName("loginStatus")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        layout.addSpacing(6)

        self.login_button = QPushButton("Sign In")
        self.login_button.setObjectName("primaryButton")
        self.login_button.setMinimumHeight(46)
        self.login_button.setCursor(Qt.PointingHandCursor)
        self.login_button.clicked.connect(self.login)
        self.server_input.returnPressed.connect(self.login)
        self.username.returnPressed.connect(self.login)
        self.password.returnPressed.connect(self.login)
        layout.addWidget(self.login_button)

        layout.addStretch(2)
        server_caption = QLabel("💡 You can customize the server URL above. It will be remembered automatically.")
        server_caption.setObjectName("serverCaption")
        server_caption.setWordWrap(True)
        layout.addWidget(server_caption)
        return panel

    @staticmethod
    def clean_server_url(raw_url):
        url = str(raw_url or "").strip()
        if not url:
            return ""
        if not (url.startswith("http://") or url.startswith("https://")):
            url = f"http://{url}"
        return url.rstrip("/")

    def login(self):
        server_val = self.clean_server_url(self.server_input.text())
        if not server_val:
            self.set_status("Please enter a valid Server URL", "error")
            self.server_input.setFocus()
            return

        if not self.username.text().strip() or not self.password.text():
            self.set_status("Please enter username and password", "error")
            return

        self.client.server_url = server_val
        self.server_input.setText(server_val)

        try:
            doc_type_id = getattr(self.client, "document_type_id", DOCUMENT_TYPE_ID)
            save_settings(server_val, doc_type_id)
        except Exception:
            pass

        self.login_button.setEnabled(False)
        self.login_button.setText("Connecting...")
        self.set_status("Connecting to server and authenticating...", "info")
        self.worker = Worker(self.client.login, self.username.text().strip(), self.password.text(), parent=self)
        self.worker.finished.connect(lambda _: self.login_ok())
        self.worker.failed.connect(self.login_failed)
        self.worker.start()

    def set_status(self, text, kind="info"):
        self.status.setText(text)
        self.status.setProperty("state", kind)
        self.status.style().unpolish(self.status)
        self.status.style().polish(self.status)

    def login_ok(self):
        self.logged_in.emit(self.client)
        self.close()

    def login_failed(self, message):
        self.set_status("Connection or sign-in failed", "error")
        self.login_button.setEnabled(True)
        self.login_button.setText("Sign In")
        err_lower = str(message).lower()
        if any(term in err_lower for term in ("max retries exceeded", "failed to establish a new connection", "connection refused", "timed out", "connecttimeouterror")):
            friendly = (
                f"Could not connect to the archive server at:\n{self.client.server_url}\n\n"
                "Please verify that:\n"
                "1. The server address and port are correct.\n"
                "2. Your device is connected to the network.\n"
                "3. The Mayan EDMS service is running on the host."
            )
            QMessageBox.critical(self, "Server Connection Error", friendly)
        else:
            QMessageBox.critical(self, "Sign In Error", message)


STYLESHEET = f"""
QWidget {{ font-family: {FONT_STACK}; font-size: 10.5pt; color: {TEXT}; }}
QMainWindow, #root {{ background: {BG}; }}

/* ---------- sidebar ---------- */
#sidebar {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {SIDEBAR_TOP}, stop:1 {SIDEBAR_BOTTOM});
    border-right: 1px solid rgba(255, 255, 255, 0.05);
}}
#sidebarMark {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {ACCENT}, stop:1 {MINT});
    color: white; font-size: 15pt; font-weight: 800; border-radius: 12px;
}}
#brand {{ color: #ffffff; font-size: 13pt; font-weight: 800; letter-spacing: 0.5px; }}
#brandCaption {{ color: #94a3b8; font-size: 8.5pt; }}
#sidebarDivider {{ background: rgba(255, 255, 255, 0.08); border: none; }}
#navButton, #navActive {{
    text-align: left; color: #cbd5e1; background: transparent; border: none;
    border-radius: 12px; padding: 0 16px; font-size: 10.5pt; font-weight: 600;
}}
#navButton:hover {{ background: rgba(255, 255, 255, 0.08); color: #ffffff; }}
#navActive {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {ACCENT}, stop:1 {ACCENT_DARK});
    color: #ffffff; font-weight: 700;
}}
#avatarBadge {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1e293b, stop:1 #334155);
    color: {MINT}; border: 1.5px solid rgba(6, 182, 212, 0.4);
    border-radius: 18px; font-weight: 800;
}}
#userName {{ color: #ffffff; font-weight: 700; font-size: 9.5pt; }}
#userState {{ color: #34d399; font-size: 8pt; font-weight: 600; }}
#logoutButton {{
    text-align: left; color: #fca5a5; background: rgba(239, 68, 68, 0.06);
    border: 1px solid rgba(239, 68, 68, 0.25);
    border-radius: 12px; padding: 0 16px; font-weight: 600;
}}
#logoutButton:hover {{ background: rgba(239, 68, 68, 0.16); border-color: {DANGER}; color: #ffffff; }}

/* ---------- header ---------- */
#pageTitle {{ font-size: 17pt; font-weight: 800; color: {TEXT}; }}
#pageSubtitle {{ font-size: 9.5pt; color: {MUTED}; }}
#chip {{
    background: {SURFACE}; color: {MUTED}; border: 1px solid {BORDER};
    border-radius: 16px; padding: 6px 14px; font-size: 9pt; font-weight: 600;
}}
#statusChip {{
    background: #f1f5f9; color: #475569; border-radius: 16px;
    padding: 6px 14px; font-size: 9pt; font-weight: 700;
}}
#statusChip[state="busy"]    {{ background: #eff6ff; color: #1d4ed8; }}
#statusChip[state="success"] {{ background: {SUCCESS_LIGHT}; color: {SUCCESS_DARK}; }}
#statusChip[state="error"]   {{ background: {DANGER_LIGHT}; color: {DANGER}; }}

/* ---------- cards & panels ---------- */
#card {{
    background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 18px;
}}
#sectionTitle {{
    font-size: 11pt; font-weight: 700; color: {TEXT};
}}
#divider {{ background: {BORDER}; border: none; }}

/* ---------- form elements ---------- */
#fieldLabel {{
    font-size: 9pt; font-weight: 600; color: {MUTED};
}}
QLineEdit, QTextEdit, QComboBox {{
    background: {SURFACE}; border: 1.5px solid {BORDER};
    border-radius: 10px; padding: 8px 14px; font-size: 10pt; color: {TEXT};
}}
QLineEdit:hover, QTextEdit:hover, QComboBox:hover {{
    border-color: #cbd5e1;
}}
QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{
    border-color: {ACCENT}; background: #ffffff;
}}
QComboBox::drop-down {{
    subcontrol-origin: padding; subcontrol-position: top right;
    width: 32px; border: none;
}}
QComboBox::down-arrow {{
    width: 10px; height: 10px;
}}
QComboBox QAbstractItemView {{
    background: {SURFACE}; border: 1px solid {BORDER};
    selection-background-color: {ACCENT_LIGHT}; selection-color: {ACCENT};
    padding: 4px; border-radius: 8px;
}}

/* ---------- buttons ---------- */
#primaryButton {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {ACCENT}, stop:1 {ACCENT_DARK});
    color: white; border: none; border-radius: 10px;
    font-weight: 700; font-size: 10pt; padding: 0 20px;
}}
#primaryButton:hover {{ background: {ACCENT_DARK}; }}
#primaryButton:disabled {{ background: #94a3b8; color: #e2e8f0; }}

#successButton {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {SUCCESS}, stop:1 {SUCCESS_DARK});
    color: white; border: none; border-radius: 10px;
    font-weight: 700; font-size: 10pt; padding: 0 20px;
}}
#successButton:hover {{ background: {SUCCESS_DARK}; }}
#successButton:disabled {{ background: #94a3b8; color: #e2e8f0; }}

#ghostButton {{
    background: transparent; color: {MUTED}; border: 1.5px solid {BORDER};
    border-radius: 10px; font-weight: 600; font-size: 9.5pt; padding: 0 14px;
}}
#ghostButton:hover {{
    background: #f1f5f9; color: {TEXT}; border-color: #cbd5e1;
}}

#filePill {{
    background: #f8fafc; color: {MUTED}; border: 1px dashed #cbd5e1;
    border-radius: 10px; padding: 10px 14px; font-size: 9pt;
}}

/* ---------- table ---------- */
QTableWidget {{
    background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 12px;
    gridline-color: #f1f5f9; outline: none;
}}
QTableWidget::item {{
    padding: 10px 12px; border-bottom: 1px solid #f1f5f9;
}}
QTableWidget::item:selected {{
    background: {ACCENT_LIGHT}; color: {ACCENT_DARK}; font-weight: 600;
}}
QHeaderView::section {{
    background: #f8fafc; color: {MUTED}; font-weight: 700; font-size: 8.5pt;
    border: none; border-bottom: 1.5px solid {BORDER}; padding: 8px 12px;
    text-transform: uppercase; text-align: left;
}}

/* ---------- login screen ---------- */
#brandPanel {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {SIDEBAR_TOP}, stop:1 {SIDEBAR_BOTTOM});
    border-right: 1px solid rgba(255, 255, 255, 0.05);
}}
#brandMark {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {ACCENT}, stop:1 {MINT});
    color: white; font-size: 26pt; font-weight: 800; border-radius: 20px;
}}
#brandTitle {{ color: #ffffff; font-size: 20pt; font-weight: 800; }}
#brandSubtitle {{ color: #94a3b8; font-size: 10pt; line-height: 1.5; }}
#brandBullet {{ color: {MINT}; font-size: 8pt; }}
#brandFeature {{ color: #e2e8f0; font-size: 9.5pt; }}

#loginPanel {{ background: {SURFACE}; }}
#loginHeading {{ font-size: 20pt; font-weight: 800; color: {TEXT}; }}
#loginStatus {{ font-size: 9pt; min-height: 18px; }}
#loginStatus[state="info"]  {{ color: {ACCENT}; }}
#loginStatus[state="error"] {{ color: {DANGER}; font-weight: 600; }}
#serverCaption {{ color: #94a3b8; font-size: 8.5pt; font-style: italic; }}
"""
