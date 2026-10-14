"""عميل Mayan EDMS REST API v4 مع دعم Caching وإدارة رموز المصادقة."""
from __future__ import annotations

import tempfile
import time
from pathlib import Path
from typing import Any

import requests

from app.utils.translations import tr


class ArchiveClient:
    """
    طبقة التواصل مع Mayan EDMS REST API v4.

    الميزات:
    - توثيق عبر Token (login / logout)
    - Caching لأنواع المستندات مدته 300 ثانية (قابل للضبط)
    - Caching لقائمة الأجهزة مدته 120 ثانية
    - جميع رسائل الخطأ مُحمّلة من ملف الترجمة
    """

    DOC_TYPES_TTL = 300   # ثانية
    DEVICES_TTL   = 120   # ثانية — يُستخدم من طبقة UI

    def __init__(self, server_url: str, document_type_id: int) -> None:
        self.server_url       = server_url.rstrip("/")
        self.document_type_id = document_type_id
        self.session          = requests.Session()
        self.token            = ""
        self.username         = ""
        self.user_id: int | None = None

        # --- Caches ---
        self._doc_types_cache: list[dict] = []
        self._doc_types_fetched_at: float = 0.0

    # ------------------------------------------------------------------ #
    #  خصائص مساعدة                                                       #
    # ------------------------------------------------------------------ #

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Token {self.token}", "Accept": "application/json"}

    @property
    def is_authenticated(self) -> bool:
        return bool(self.token)

    # ------------------------------------------------------------------ #
    #  المصادقة                                                           #
    # ------------------------------------------------------------------ #

    def login(self, username: str, password: str) -> None:
        """تسجيل الدخول والحصول على رمز المصادقة."""
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
                tr("client_errors", "connect_timeout", server_url=self.server_url)
            )
        except requests.exceptions.ReadTimeout:
            raise RuntimeError(tr("client_errors", "read_timeout"))
        except requests.exceptions.ConnectionError as error:
            raise RuntimeError(
                tr("client_errors", "connection_error",
                   server_url=self.server_url, error=error)
            )

        if response.status_code not in (200, 201):
            try:
                detail = response.json()
            except ValueError:
                detail = response.text[:500]
            raise RuntimeError(
                tr("client_errors", "auth_failed",
                   status_code=response.status_code, detail=detail)
            )

        data = response.json()
        self.token = (
            data.get("token") or data.get("key") or data.get("auth_token", "")
        )
        if not self.token:
            raise RuntimeError(tr("client_errors", "no_token", data=data))
        self.username = username
        # مسح الكاش عند إعادة الدخول
        self.invalidate_doc_types_cache()
        self._load_current_user()

    def logout(self) -> None:
        """مسح رمز المصادقة وإعادة تعيين الجلسة."""
        self.token = ""
        self.username = ""
        self.user_id = None
        self.invalidate_doc_types_cache()
        self.session = requests.Session()

    def _load_current_user(self) -> None:
        """جلب معرّف المستخدم الحالي بعد تسجيل الدخول."""
        try:
            resp = self.session.get(
                f"{self.server_url}/api/v4/users/current/",
                headers=self.headers, timeout=(5, 15),
            )
            if resp.status_code == 200:
                data = resp.json()
                info = self._unwrap_document(data) if isinstance(data, dict) else {}
                info = info or (data if isinstance(data, dict) else {})
                if info.get("id") is not None:
                    self.user_id = info["id"]
                    return
        except (requests.exceptions.RequestException, ValueError):
            pass

        try:
            resp = self.session.get(
                f"{self.server_url}/api/v4/users/",
                headers=self.headers,
                params={"page_size": 200},
                timeout=(5, 15),
            )
            if resp.status_code != 200:
                return
            for raw in resp.json().get("results", []):
                item = raw.get("entry", raw) if isinstance(raw, dict) else {}
                if item.get("username") == self.username:
                    self.user_id = item.get("id")
                    return
        except (requests.exceptions.RequestException, ValueError):
            return

    # ------------------------------------------------------------------ #
    #  أنواع المستندات — مع Caching                                       #
    # ------------------------------------------------------------------ #

    def invalidate_doc_types_cache(self) -> None:
        """إبطال كاش أنواع المستندات لإجبار إعادة الجلب."""
        self._doc_types_cache = []
        self._doc_types_fetched_at = 0.0

    def document_types(self, force_refresh: bool = False) -> list[dict]:
        """
        إرجاع قائمة أنواع المستندات.
        تُستخدم النتيجة المخزّنة في الكاش طالما لم يمرّ DOC_TYPES_TTL ثانية.
        """
        now = time.monotonic()
        if (
            not force_refresh
            and self._doc_types_cache
            and (now - self._doc_types_fetched_at) < self.DOC_TYPES_TTL
        ):
            return self._doc_types_cache

        response = self.session.get(
            f"{self.server_url}/api/v4/document_types/",
            headers=self.headers,
            params={"page_size": 100},
            timeout=(5, 15),
        )
        if response.status_code != 200:
            try:
                detail = response.json()
            except ValueError:
                detail = response.text[:500]
            raise RuntimeError(
                tr("client_errors", "doc_types_failed",
                   status_code=response.status_code, detail=detail)
            )

        data  = response.json()
        items = (
            data.get("results")
            or data.get("list", {}).get("results")
            or data.get("list", {}).get("entries")
            or []
        )
        types: list[dict] = []
        for raw in items:
            item = raw.get("entry", raw) if isinstance(raw, dict) else {}
            if item.get("id") is not None:
                types.append({"id": item["id"], "label": item.get("label", str(item["id"]))})

        self._doc_types_cache = types
        self._doc_types_fetched_at = now
        return types

    # ------------------------------------------------------------------ #
    #  الأرشفة                                                            #
    # ------------------------------------------------------------------ #

    def archive(
        self,
        pdf_path: str | Path,
        number: str,
        title: str,
        date: str,
        notes: str = "",
        document_type_id: int | None = None,
    ) -> dict:
        """إنشاء سجل المستند ورفع ملف PDF إلى خادم الأرشيف."""
        selected_type_id = int(document_type_id or self.document_type_id)
        payload = {
            "document_type_id": selected_type_id,
            "label": f"{number} - {title}",
            "description": f"التاريخ: {date}\nملاحظات: {notes}".strip(),
        }

        create_resp = self.session.post(
            f"{self.server_url}/api/v4/documents/",
            headers=self.headers,
            data=payload,
            timeout=(5, 30),
        )
        if create_resp.status_code not in (200, 201):
            try:
                detail: Any = create_resp.json()
            except ValueError:
                detail = create_resp.text[:1000]
            raise RuntimeError(
                tr("client_errors", "create_failed",
                   status_code=create_resp.status_code,
                   detail=detail,
                   type_id=selected_type_id)
            )

        result       = create_resp.json() if create_resp.content else {}
        document_obj = self._unwrap_document(result)
        document_id  = (
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
            raise RuntimeError(
                tr("client_errors", "missing_doc_id", result=result)
            )

        # التحقق من وجود المستند
        verify_resp = self.session.get(
            f"{self.server_url}/api/v4/documents/{int(document_id)}/",
            headers=self.headers,
            timeout=(5, 30),
        )
        if verify_resp.status_code != 200:
            raise RuntimeError(
                tr("client_errors", "verify_failed",
                   status_code=verify_resp.status_code,
                   document_id=document_id)
            )

        # رفع الملف
        with Path(pdf_path).open("rb") as stream:
            file_resp = self.session.post(
                f"{self.server_url}/api/v4/documents/{int(document_id)}/files/",
                headers=self.headers,
                data={"action_name": "replace"},
                files={"file_new": (Path(pdf_path).name, stream, "application/pdf")},
                timeout=(5, 180),
            )
        if file_resp.status_code not in (200, 201, 202):
            try:
                detail = file_resp.json()
            except ValueError:
                detail = file_resp.text[:1000]
            raise RuntimeError(
                tr("client_errors", "upload_failed",
                   document_id=document_id,
                   status_code=file_resp.status_code,
                   detail=detail)
            )

        if isinstance(result, dict) and file_resp.content:
            try:
                result["file_upload"] = file_resp.json()
            except ValueError:
                pass
        return result

    # ------------------------------------------------------------------ #
    #  التنزيل                                                            #
    # ------------------------------------------------------------------ #

    def download_document(self, document_id: int | str) -> str:
        """تنزيل أحدث ملف للمستند وإعادة المسار المحلي المؤقت."""
        document_id = int(document_id)
        base        = f"{self.server_url}/api/v4/documents/{document_id}"
        candidates: list[str] = []

        # 1. تفاصيل المستند
        detail_resp = self.session.get(
            f"{base}/", headers=self.headers, timeout=(5, 30)
        )
        detail: dict = {}
        if detail_resp.status_code == 200:
            detail_data = detail_resp.json()
            detail = (
                detail_data.get("entry", detail_data)
                if isinstance(detail_data, dict)
                else {}
            )
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

        # 2. قائمة ملفات المستند
        files_url = (
            detail.get("files_url")
            or detail.get("document_files_url")
            or f"{base}/files/"
        )
        try:
            files_resp = self.session.get(
                files_url, headers=self.headers, timeout=(5, 30)
            )
            if files_resp.status_code == 200:
                files_data = files_resp.json()
                results = (
                    files_data.get("results")
                    or files_data.get("objects")
                    or files_data.get("items")
                    or []
                )
                if isinstance(results, list):
                    for f_entry in reversed(results):
                        f_item = (
                            f_entry.get("entry", f_entry)
                            if isinstance(f_entry, dict)
                            else {}
                        )
                        if (
                            f_item.get("download_url")
                            and f_item["download_url"] not in candidates
                        ):
                            candidates.append(f_item["download_url"])
                        f_id = f_item.get("id")
                        if f_id is not None:
                            f_url = f"{base}/files/{f_id}/download/"
                            if f_url not in candidates:
                                candidates.append(f_url)
        except Exception:
            pass

        # 3. روابط احتياطية
        for fallback in (f"{base}/download/", f"{base}/file/"):
            if fallback not in candidates:
                candidates.append(fallback)

        last_status: int | None = None
        last_body = ""
        for download_url in candidates:
            if download_url.startswith("/"):
                download_url = f"{self.server_url}{download_url}"
            elif not download_url.startswith("http"):
                download_url = f"{self.server_url}/{download_url.lstrip('/')}"

            try:
                resp = self.session.get(
                    download_url,
                    headers=self.headers,
                    timeout=(5, 180),
                    stream=True,
                )
            except Exception as exc:
                last_body = str(exc)
                continue

            last_status = resp.status_code
            if resp.status_code != 200:
                try:
                    last_body = resp.text[:500]
                except Exception:
                    pass
                continue

            content_type = resp.headers.get("content-type", "").lower()
            if "application/json" in content_type or "text/html" in content_type:
                last_body = tr(
                    "client_errors", "skip_metadata",
                    content_type=content_type, url=download_url
                )
                continue

            suffix = ".pdf"
            cd = resp.headers.get("content-disposition", "")
            if "filename=" in cd:
                fname = cd.split("filename=")[-1].strip("\"' ;")
                ext = Path(fname).suffix.lower()
                if ext in (".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif", ".txt", ".docx", ".xlsx"):
                    suffix = ext
            elif "image/jpeg" in content_type:
                suffix = ".jpg"
            elif "image/png" in content_type:
                suffix = ".png"
            elif "image/tiff" in content_type:
                suffix = ".tiff"

            first_chunk    = True
            is_valid_binary = True
            with tempfile.NamedTemporaryFile(
                prefix=f"archive_doc_{document_id}_", suffix=suffix, delete=False
            ) as output:
                for chunk in resp.iter_content(chunk_size=1024 * 256):
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
            tr("client_errors", "download_failed",
               status_code=last_status, detail=last_body)
        )

    # ------------------------------------------------------------------ #
    #  البحث                                                              #
    # ------------------------------------------------------------------ #

    def search(self, query: str) -> list[dict]:
        """البحث في الأرشيف بالنص والإعادة كقائمة عناصر."""
        query = str(query).strip()
        if not query:
            return []

        response = self.session.get(
            f"{self.server_url}/api/v4/search/",
            headers=self.headers,
            params={"q": query},
            timeout=60,
        )
        if response.status_code != 200:
            # Fallback: جلب كل الوثائق والتصفية محليًا
            response = self.session.get(
                f"{self.server_url}/api/v4/documents/",
                headers=self.headers,
                params={"page_size": 100},
                timeout=60,
            )
        if response.status_code != 200:
            try:
                detail: Any = response.json()
            except ValueError:
                detail = response.text[:500]
            raise RuntimeError(
                tr("client_errors", "search_failed",
                   status_code=response.status_code, detail=detail)
            )

        data   = response.json()
        items  = (
            data.get("results")
            or data.get("list", {}).get("results", [])
            or []
        )
        needle        = self._normalise_digits(query)
        numeric_query = needle.isdigit()
        filtered: list[dict] = []
        for raw in items:
            item        = self._unwrap_document(raw)
            label       = str(item.get("label", "")).strip()
            description = str(item.get("description", "")).strip()
            number      = label.split(" - ", 1)[0].strip() if " - " in label else label
            if numeric_query:
                norm_num = self._normalise_digits(number)
                digits_only = "".join(ch for ch in norm_num if ch.isdigit())
                matches = (norm_num == needle) or (digits_only == needle)
            else:
                searchable = self._normalise_digits(f"{label} {description}")
                matches    = needle in searchable
            if matches:
                filtered.append(item)
        return filtered

    # ------------------------------------------------------------------ #
    #  أدوات مساعدة (Static)                                              #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _unwrap_document(raw: Any) -> dict:
        """استخراج قاموس المستند الداخلي من استجابات متعددة البنية."""
        if not isinstance(raw, dict):
            return {}
        for key in ("document", "object", "entry", "result"):
            nested = raw.get(key)
            if isinstance(nested, dict) and ("label" in nested or "id" in nested):
                return nested
        return raw

    @staticmethod
    def _normalise_digits(value: Any) -> str:
        """تحويل الأرقام العربية/الفارسية إلى أرقام لاتينية وتقليل الحروف."""
        table = str.maketrans(
            "٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹",
            "01234567890123456789"
        )
        return str(value).translate(table).strip().casefold()
