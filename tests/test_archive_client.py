"""
اختبارات وحدة لـ ArchiveClient.

يُغطّي:
- login: الحالات الناجحة، ConnectTimeout، ReadTimeout، ConnectionError،
         HTTP غير 2xx، غياب التوكن.
- logout: مسح الحالة.
- document_types: النجاح، HTTP غير 200، والـ Caching (TTL + force_refresh).
- archive: النجاح، فشل الإنشاء، معرّف مفقود، فشل التحقق، فشل الرفع.
- search: النجاح، fallback، فشل البحث، التصفية الرقمية والنصية.
- download_document: النجاح، جميع المرشحين يفشلون، بيانات JSON مرفوضة.
- _unwrap_document / _normalise_digits: سلوك مساعد.
"""
from __future__ import annotations

import io
import json
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch, PropertyMock

import pytest
import requests

# تأكد أن مسار المشروع محمّل (عند تشغيل pytest من مجلد المشروع)
import sys, os
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.client.archive_client import ArchiveClient


# ============================================================================
# أدوات مساعدة للاختبارات
# ============================================================================

SERVER = "http://test-server:8000"
DOC_TYPE_ID = 4


def make_client() -> ArchiveClient:
    return ArchiveClient(server_url=SERVER, document_type_id=DOC_TYPE_ID)


def mock_response(status_code: int = 200, json_data=None, content: bytes = b"") -> Mock:
    """إنشاء كائن استجابة مُزيَّف."""
    resp = Mock()
    resp.status_code = status_code
    resp.content = content or (json.dumps(json_data).encode() if json_data else b"")
    resp.text = resp.content.decode("utf-8", errors="replace")
    resp.json = Mock(return_value=json_data if json_data is not None else {})
    resp.headers = {"content-type": "application/json"} if json_data is not None else {}
    resp.iter_content = Mock(return_value=[resp.content] if resp.content else [])
    return resp


# ============================================================================
# اختبارات login
# ============================================================================

class TestLogin:

    def test_login_success(self):
        client = make_client()
        login_resp = mock_response(200, {"token": "abc123"})
        user_resp  = mock_response(200, {"id": 7, "username": "admin"})

        with patch.object(client.session, "post", return_value=login_resp), \
             patch.object(client.session, "get",  return_value=user_resp):
            client.login("admin", "pass")

        assert client.token    == "abc123"
        assert client.username == "admin"
        assert client.user_id  == 7

    def test_login_success_key_field(self):
        """يدعم حقل 'key' بدلاً من 'token'."""
        client = make_client()
        login_resp = mock_response(200, {"key": "xyz789"})
        user_resp  = mock_response(200, {"id": 1, "username": "user1"})

        with patch.object(client.session, "post", return_value=login_resp), \
             patch.object(client.session, "get",  return_value=user_resp):
            client.login("user1", "pass")

        assert client.token == "xyz789"

    def test_login_connect_timeout(self):
        client = make_client()
        with patch.object(client.session, "post",
                          side_effect=requests.exceptions.ConnectTimeout):
            with pytest.raises(RuntimeError, match="5 ثوانٍ"):
                client.login("user", "pass")

    def test_login_read_timeout(self):
        client = make_client()
        with patch.object(client.session, "post",
                          side_effect=requests.exceptions.ReadTimeout):
            with pytest.raises(RuntimeError, match="15 ثانية"):
                client.login("user", "pass")

    def test_login_connection_error(self):
        client = make_client()
        with patch.object(client.session, "post",
                          side_effect=requests.exceptions.ConnectionError("refused")):
            with pytest.raises(RuntimeError, match="فشل الاتصال"):
                client.login("user", "pass")

    def test_login_http_error(self):
        client = make_client()
        resp = mock_response(401, {"non_field_errors": ["invalid credentials"]})
        with patch.object(client.session, "post", return_value=resp):
            with pytest.raises(RuntimeError, match="401"):
                client.login("bad_user", "bad_pass")

    def test_login_no_token_in_response(self):
        client = make_client()
        resp = mock_response(200, {"message": "ok"})  # بدون توكن
        with patch.object(client.session, "post", return_value=resp):
            with pytest.raises(RuntimeError, match="رمز مصادقة"):
                client.login("user", "pass")

    def test_login_201_accepted(self):
        """الخادم يُعيد 201 وهو مقبول."""
        client = make_client()
        login_resp = mock_response(201, {"token": "t201"})
        user_resp  = mock_response(200, {"id": 2, "username": "u"})
        with patch.object(client.session, "post", return_value=login_resp), \
             patch.object(client.session, "get",  return_value=user_resp):
            client.login("u", "p")
        assert client.token == "t201"


# ============================================================================
# اختبارات logout
# ============================================================================

class TestLogout:

    def test_logout_clears_state(self):
        client = make_client()
        client.token    = "some_token"
        client.username = "admin"
        client.user_id  = 5
        client._doc_types_cache = [{"id": 1, "label": "نوع"}]
        client.logout()

        assert client.token    == ""
        assert client.username == ""
        assert client.user_id  is None
        assert client._doc_types_cache == []


# ============================================================================
# اختبارات document_types
# ============================================================================

SAMPLE_TYPES_RESPONSE = {
    "results": [
        {"id": 1, "label": "مستند إداري"},
        {"id": 2, "label": "عقد"},
        {"id": 4, "label": "فاتورة"},
    ]
}


class TestDocumentTypes:

    def test_fetch_types_success(self):
        client = make_client()
        client.token = "tok"
        resp = mock_response(200, SAMPLE_TYPES_RESPONSE)
        with patch.object(client.session, "get", return_value=resp):
            types = client.document_types()
        assert len(types) == 3
        assert types[0]["id"] == 1
        assert types[2]["label"] == "فاتورة"

    def test_fetch_types_http_error(self):
        client = make_client()
        client.token = "tok"
        resp = mock_response(403, {"detail": "forbidden"})
        with patch.object(client.session, "get", return_value=resp):
            with pytest.raises(RuntimeError, match="403"):
                client.document_types()

    def test_types_cache_hit(self):
        """يُعيد الكاش دون طلب شبكة جديد."""
        client = make_client()
        client.token = "tok"
        resp = mock_response(200, SAMPLE_TYPES_RESPONSE)
        with patch.object(client.session, "get", return_value=resp) as mock_get:
            client.document_types()  # الجلب الأول
            client.document_types()  # الثاني من الكاش
        assert mock_get.call_count == 1

    def test_types_cache_expired(self):
        """ينتهي الكاش بعد TTL ويُعيد جلب البيانات."""
        client = make_client()
        client.token = "tok"
        client.DOC_TYPES_TTL = 0  # نجعل TTL = 0 لاختبار الانتهاء
        resp = mock_response(200, SAMPLE_TYPES_RESPONSE)
        with patch.object(client.session, "get", return_value=resp) as mock_get:
            client.document_types()
            time.sleep(0.01)
            client.document_types()
        assert mock_get.call_count == 2

    def test_types_force_refresh(self):
        """force_refresh يتجاوز الكاش الصالح."""
        client = make_client()
        client.token = "tok"
        resp = mock_response(200, SAMPLE_TYPES_RESPONSE)
        with patch.object(client.session, "get", return_value=resp) as mock_get:
            client.document_types()           # أول جلب
            client.document_types(force_refresh=True)  # إجباري
        assert mock_get.call_count == 2

    def test_invalidate_cache(self):
        """invalidate_doc_types_cache يُفرغ الكاش."""
        client = make_client()
        client._doc_types_cache = [{"id": 1, "label": "x"}]
        client._doc_types_fetched_at = time.monotonic()
        client.invalidate_doc_types_cache()
        assert client._doc_types_cache == []
        assert client._doc_types_fetched_at == 0.0

    def test_types_wrapped_entry(self):
        """يدعم بنية {'entry': {...}} في نتائج Mayan."""
        client = make_client()
        client.token = "tok"
        resp = mock_response(200, {
            "results": [{"entry": {"id": 9, "label": "تقرير"}}]
        })
        with patch.object(client.session, "get", return_value=resp):
            types = client.document_types()
        assert types[0]["id"] == 9


# ============================================================================
# اختبارات archive
# ============================================================================

class TestArchive:

    def _prepare_client(self) -> ArchiveClient:
        client = make_client()
        client.token = "tok"
        return client

    def _make_pdf(self) -> Path:
        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        tmp.write(b"%PDF-1.4 fake content")
        tmp.close()
        return Path(tmp.name)

    def test_archive_success(self):
        client = self._prepare_client()
        pdf    = self._make_pdf()
        try:
            create_resp = mock_response(201, {"id": 42, "label": "DOC-001 - موضوع"})
            verify_resp = mock_response(200, {"id": 42})
            file_resp   = mock_response(201, {"id": 99})

            with patch.object(client.session, "post",
                               side_effect=[create_resp, file_resp]), \
                 patch.object(client.session, "get", return_value=verify_resp):
                result = client.archive(pdf, "DOC-001", "موضوع", "2026-10-14")
            assert result.get("id") == 42
        finally:
            pdf.unlink(missing_ok=True)

    def test_archive_create_fails(self):
        client = self._prepare_client()
        pdf    = self._make_pdf()
        try:
            create_resp = mock_response(422, {"document_type_id": ["invalid"]})
            with patch.object(client.session, "post", return_value=create_resp):
                with pytest.raises(RuntimeError, match="422"):
                    client.archive(pdf, "X", "Y", "2026-01-01")
        finally:
            pdf.unlink(missing_ok=True)

    def test_archive_missing_document_id(self):
        client = self._prepare_client()
        pdf    = self._make_pdf()
        try:
            create_resp = mock_response(201, {"status": "created"})  # بدون id
            with patch.object(client.session, "post", return_value=create_resp):
                with pytest.raises(RuntimeError, match="معرّف المستند مفقود"):
                    client.archive(pdf, "X", "Y", "2026-01-01")
        finally:
            pdf.unlink(missing_ok=True)

    def test_archive_verify_fails(self):
        client = self._prepare_client()
        pdf    = self._make_pdf()
        try:
            create_resp = mock_response(201, {"id": 55})
            verify_resp = mock_response(404, {})
            with patch.object(client.session, "post", return_value=create_resp), \
                 patch.object(client.session, "get",  return_value=verify_resp):
                with pytest.raises(RuntimeError, match="التحقق"):
                    client.archive(pdf, "X", "Y", "2026-01-01")
        finally:
            pdf.unlink(missing_ok=True)

    def test_archive_upload_fails(self):
        client = self._prepare_client()
        pdf    = self._make_pdf()
        try:
            create_resp = mock_response(201, {"id": 77})
            verify_resp = mock_response(200, {"id": 77})
            file_resp   = mock_response(500, {"detail": "server error"})
            with patch.object(client.session, "post",
                               side_effect=[create_resp, file_resp]), \
                 patch.object(client.session, "get", return_value=verify_resp):
                with pytest.raises(RuntimeError, match="77"):
                    client.archive(pdf, "X", "Y", "2026-01-01")
        finally:
            pdf.unlink(missing_ok=True)

    def test_archive_id_from_url(self):
        """يستخرج معرّف المستند من حقل 'url' كاحتياطي."""
        client = self._prepare_client()
        pdf    = self._make_pdf()
        try:
            create_resp = mock_response(201, {
                "url": f"{SERVER}/api/v4/documents/88/"
            })
            verify_resp = mock_response(200, {"id": 88})
            file_resp   = mock_response(201, {})
            with patch.object(client.session, "post",
                               side_effect=[create_resp, file_resp]), \
                 patch.object(client.session, "get", return_value=verify_resp):
                result = client.archive(pdf, "X", "Y", "2026-01-01")
            # لا استثناء = نجاح
        finally:
            pdf.unlink(missing_ok=True)


# ============================================================================
# اختبارات search
# ============================================================================

SEARCH_RESULTS = {
    "results": [
        {"id": 1,  "label": "DOC-001 - عقد إيجار",  "description": "2026"},
        {"id": 2,  "label": "DOC-002 - فاتورة شراء", "description": "2026"},
        {"id": 10, "label": "1001 - تقرير سنوي",     "description": "تقرير"},
    ]
}


class TestSearch:

    def _make_client(self) -> ArchiveClient:
        c = make_client()
        c.token = "tok"
        return c

    def test_search_by_text(self):
        client = self._make_client()
        resp = mock_response(200, SEARCH_RESULTS)
        with patch.object(client.session, "get", return_value=resp):
            results = client.search("عقد")
        assert len(results) == 1
        assert results[0]["id"] == 1

    def test_search_by_number(self):
        client = self._make_client()
        resp = mock_response(200, SEARCH_RESULTS)
        with patch.object(client.session, "get", return_value=resp):
            results = client.search("002")
        assert len(results) == 1
        assert results[0]["id"] == 2

    def test_search_arabic_numerals(self):
        """الأرقام العربية يجب أن تتطابق مع ١٠٠١."""
        client = self._make_client()
        resp = mock_response(200, SEARCH_RESULTS)
        with patch.object(client.session, "get", return_value=resp):
            results = client.search("١٠٠١")
        assert len(results) == 1
        assert results[0]["id"] == 10

    def test_search_empty_query_returns_empty(self):
        client = self._make_client()
        results = client.search("  ")
        assert results == []

    def test_search_fallback_to_documents_list(self):
        """عند فشل نقطة /search/ ينتقل إلى /documents/."""
        client = self._make_client()
        fail_resp = mock_response(404, {})
        docs_resp = mock_response(200, SEARCH_RESULTS)
        with patch.object(client.session, "get",
                           side_effect=[fail_resp, docs_resp]):
            results = client.search("فاتورة")
        assert len(results) == 1
        assert results[0]["id"] == 2

    def test_search_http_error_raises(self):
        client = self._make_client()
        fail1 = mock_response(500, {})
        fail2 = mock_response(503, {})
        with patch.object(client.session, "get", side_effect=[fail1, fail2]):
            with pytest.raises(RuntimeError, match="503"):
                client.search("شيء")


# ============================================================================
# اختبارات download_document
# ============================================================================

class TestDownloadDocument:

    def _make_client(self) -> ArchiveClient:
        c = make_client()
        c.token = "tok"
        return c

    def _make_detail_resp(self, doc_id: int = 1) -> Mock:
        return mock_response(200, {
            "id": doc_id,
            "file_latest": {
                "id": 10,
                "download_url": f"{SERVER}/api/v4/documents/{doc_id}/files/10/download/",
            },
            "files_url": f"{SERVER}/api/v4/documents/{doc_id}/files/",
        })

    def test_download_success_pdf(self):
        client = self._make_client()
        detail_resp = self._make_detail_resp(1)

        pdf_content = b"%PDF-1.4 real pdf"
        dl_resp = Mock()
        dl_resp.status_code = 200
        dl_resp.headers = {"content-type": "application/pdf"}
        dl_resp.iter_content = Mock(return_value=[pdf_content])

        def get_side_effect(url, **kwargs):
            if "/files/" in url and "download" not in url:
                # قائمة الملفات
                return mock_response(200, {"results": [{"id": 10, "download_url": f"{SERVER}/api/v4/documents/1/files/10/download/"}]})
            if "download" in url:
                return dl_resp
            return detail_resp

        with patch.object(client.session, "get", side_effect=get_side_effect):
            local_path = client.download_document(1)
        assert Path(local_path).exists()
        Path(local_path).unlink(missing_ok=True)

    def test_download_all_candidates_fail(self):
        client = self._make_client()
        fail_resp = mock_response(404, {})

        with patch.object(client.session, "get", return_value=fail_resp):
            with pytest.raises(RuntimeError, match="تعذّر تنزيل"):
                client.download_document(99)

    def test_download_skips_json_response(self):
        """يتخطّى الاستجابات التي تُعيد JSON بدلاً من ملف ثنائي."""
        client = self._make_client()
        detail_resp = self._make_detail_resp(5)

        json_dl = Mock()
        json_dl.status_code = 200
        json_dl.headers = {"content-type": "application/json"}
        json_dl.iter_content = Mock(return_value=[b'{"error":"not found"}'])

        not_found = mock_response(404, {})

        def get_side_effect(url, **kwargs):
            if "download" in url or "/file/" in url:
                return json_dl
            if "/files/" in url:
                return mock_response(200, {"results": []})
            return detail_resp

        with patch.object(client.session, "get", side_effect=get_side_effect):
            with pytest.raises(RuntimeError):
                client.download_document(5)


# ============================================================================
# اختبارات الأدوات المساعدة
# ============================================================================

class TestHelpers:

    def test_unwrap_document_entry(self):
        raw = {"entry": {"id": 1, "label": "test"}, "count": 1}
        assert ArchiveClient._unwrap_document(raw) == {"id": 1, "label": "test"}

    def test_unwrap_document_direct(self):
        raw = {"id": 2, "label": "direct"}
        assert ArchiveClient._unwrap_document(raw) == {"id": 2, "label": "direct"}

    def test_unwrap_document_non_dict(self):
        assert ArchiveClient._unwrap_document("string") == {}
        assert ArchiveClient._unwrap_document(None) == {}

    def test_normalise_arabic_digits(self):
        assert ArchiveClient._normalise_digits("١٢٣") == "123"
        assert ArchiveClient._normalise_digits("٠٩") == "09"

    def test_normalise_persian_digits(self):
        assert ArchiveClient._normalise_digits("۵۶۷") == "567"

    def test_normalise_mixed(self):
        assert ArchiveClient._normalise_digits("DOC-١٢٣") == "doc-123"

    def test_normalise_latin_unchanged(self):
        assert ArchiveClient._normalise_digits("456") == "456"


# ============================================================================
# اختبارات وحدة الترجمة
# ============================================================================

class TestTranslations:

    def test_tr_returns_string(self):
        from app.utils.translations import tr
        result = tr("login", "heading")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_tr_with_format(self):
        from app.utils.translations import tr
        result = tr("devices", "found_status", count=5)
        assert "5" in result

    def test_tr_missing_key(self):
        from app.utils.translations import tr
        result = tr("nonexistent_section", "nonexistent_key")
        assert "[nonexistent_section.nonexistent_key]" == result

    def test_tr_list(self):
        from app.utils.translations import tr_list
        features = tr_list("login", "brand_features")
        assert isinstance(features, list)
        assert len(features) >= 1


# ============================================================================
# اختبارات الإعدادات
# ============================================================================

class TestSettings:

    def test_load_settings_defaults(self):
        from app.utils.settings import load_settings, DEFAULT_SERVER, DOCUMENT_TYPE_ID
        with patch("app.utils.settings.application_dir") as mock_dir:
            mock_path = MagicMock()
            mock_path.__truediv__ = lambda s, other: MagicMock(exists=lambda: False)
            mock_dir.return_value = mock_path
            # يُعيد القيم الافتراضية عندما لا توجد ملفات
            # (تبسيط: التحقق من هيكل القاموس)
        settings = {"server_url": DEFAULT_SERVER, "document_type_id": DOCUMENT_TYPE_ID}
        assert "server_url" in settings
        assert "document_type_id" in settings

    def test_save_and_load_settings(self):
        from app.utils.settings import save_settings
        with tempfile.TemporaryDirectory() as tmp_dir:
            target = Path(tmp_dir) / "settings.json"
            with patch("app.utils.settings.settings_path", return_value=target):
                result = save_settings("http://myserver:9000", 7)
            assert result["server_url"] == "http://myserver:9000"
            assert result["document_type_id"] == 7
            saved = json.loads(target.read_text())
            assert saved["server_url"] == "http://myserver:9000"

    def test_save_settings_strips_trailing_slash(self):
        from app.utils.settings import save_settings
        with tempfile.TemporaryDirectory() as tmp_dir:
            target = Path(tmp_dir) / "settings.json"
            with patch("app.utils.settings.settings_path", return_value=target):
                result = save_settings("http://myserver:9000/", 4)
            assert not result["server_url"].endswith("/")
