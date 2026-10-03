# ArchiveScanner لمساعد وخادم Mayan EDMS

<p align="center">
  <img src="assets/logo.png" alt="DocArchive Logo" width="120" height="120" />
</p>

<p align="center">
  <a href="https://github.com/bkinter17-cloud/ArchiveScanner_for_mayan_edms/releases/download/v1.0.0/ArchiveScanner-Setup.exe">
    <img src="https://img.shields.io/badge/⬇%20تحميل-مثبت%20ويندوز%20المباشر%20(.exe)-4f46e5?style=for-the-badge&logo=windows" alt="تحميل برنامج التثبيت" />
  </a>
</p>

تطبيق مكتبي متكامل لنظام تشغيل Windows يعمل كأداة مساعدة ومباشرة لنظام الأرشفة وإدارة الوثائق الإلكترونية **Mayan EDMS**.

---

## 🌟 أبرز المميزات

- **ربط مباشر بأجهزة الماسح الضوئي**: التقاط الوثائق الورقية من أجهزة السكانر عبر TWAIN / WIA باستخدام محرك NAPS2 المدمج.
- **أرشفة فورية بنقرة واحدة**: إنشاء سجل الوثيقة ورفع ملف الـ PDF مباشرة إلى خادم Mayan EDMS عبر واجهة REST API v4.
- **بحث وتنزيل فوري**: البحث برقم الوثيقة أو العنوان أو الموضوع مع إمكانية النقر المزدوج لفتح وتنزيل الوثيقة المؤرشفة.
- **تخصيص عنوان السيرفر**: إمكانية إدخال وتعديل عنوان السيرفر والمنفذ بحرية من شاشة تسجيل الدخول مع الحفظ التلقائي.
- **حزمة مستقلة بالكامل**: إمكانية بناء ملف تنفيذي ومثبت لا يتطلب من المستخدم تثبيت بايثون أو أي برامج أخرى.

---

## 🛠️ متطلبات التشغيل والتطوير

- نظام تشغيل Windows 10 أو 11 (64 بت).
- بايثون 3.11 أو 3.12.
- خادم Mayan EDMS v4 نشط ومتاح على الشبكة.

### خطوات التثبيت من المصدر

```cmd
python -m venv .venv
.venv\Scripts\activate
pip install -r qt6_windows_requirements.txt
python archive.py
```

### بناء النسخة المستقلة بواسطة PyInstaller

1. ضع نسخة NAPS2 Portable داخل المجلد:
   `build_assets\NAPS2\NAPS2.Console.exe`
2. نفّذ أمر البناء:
   ```cmd
   pyinstaller --clean --noconfirm ArchiveScannerQt.spec
   ```
3. ستجد الحزمة جاهزة داخل: `dist\ArchiveScanner\`

---

## 📄 الترخيص

هذا المشروع مرخص تحت رخصة **MIT**.
محرك NAPS2 مرخص تحت رخصة **GNU LGPL**.
