# Mayan EDMS API findings

The user's Mayan 4.12.1 API response for `GET /api/v4/documents/` showed document `id: 6`, `file_latest.id: 3`, and `version_active.id: 3`. The active version included `export_url: /api/v4/documents/6/versions/3/export/` and `file_latest.url: /api/v4/documents/6/files/3/`.

The Swagger operation for creating a version is `POST /api/v4/documents/{document_id}/versions/` with request content type `multipart/form-data`; visible fields included `document_id`, `active`, and `comment`, with a file field below the visible portion. Mayan documentation states that uploaded files correspond to document files and document versions in the v4 document page composition model, and that downloading applies to document files while exporting to PDF applies to document versions.

Sources:
- https://docs.mayan-edms.com/chapters/releases/4.0.html
- https://docs.mayan-edms.com/chapters/apps/documents/document_types.html
- https://groups.google.com/g/mayan-edms/c/NXgvSS6A6_I
