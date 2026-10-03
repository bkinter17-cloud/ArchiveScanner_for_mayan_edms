# ArchiveScanner for Mayan EDMS

<p align="center">
  <img src="assets/logo.png" alt="DocArchive Logo" width="130" height="130" />
</p>

<p align="center">
  <b>Fast, dedicated desktop scanner companion and digital archiving client for <a href="https://www.mayan-edms.com/">Mayan EDMS</a>.</b>
</p>

<p align="center">
  <a href="README_AR.md"><b>العربية</b></a> | <b>English</b>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11%20%7C%203.12-blue?logo=python" alt="Python Version" />
  <img src="https://img.shields.io/badge/GUI-PySide6%20(Qt6)-41cd52?logo=qt" alt="PySide6 Qt6" />
  <img src="https://img.shields.io/badge/Scanner-NAPS2-orange" alt="NAPS2 Scanner" />
  <img src="https://img.shields.io/badge/Backend-Mayan%20EDMS%20v4-purple" alt="Mayan EDMS" />
  <img src="https://img.shields.io/badge/Platform-Windows%20x64-0078D6?logo=windows" alt="Windows Platform" />
  <img src="https://img.shields.io/badge/License-MIT-green" alt="MIT License" />
</p>

---

## 🌟 Why ArchiveScanner?

[Mayan EDMS](https://www.mayan-edms.com/) is an enterprise-grade electronic document management system. However, capturing paper documents from desktop hardware scanners into Mayan usually requires separate scanning tools, saving intermediate files, and manually uploading them through the web interface.

**ArchiveScanner** bridges this gap:
- Connects directly to local flatbed and ADF scanners via TWAIN / WIA using a portable [NAPS2](https://www.naps2.com/) engine.
- Integrates seamlessly with Mayan EDMS REST API v4: creating document entries, populating metadata, and uploading PDF files in a single click.
- Allows users to search the archive, view results, and download/open documents with a double-click.
- Provides a clean, modern Qt6 desktop interface with customizable server connection settings.

---

## ✨ Features

- **Hardware Scanner Integration**: Auto-detects connected scanner devices and scans multi-page documents directly into clean searchable PDFs.
- **Two-Step Mayan Upload**: Fully handles Mayan v4's multi-step document creation (`POST /api/v4/documents/`) and file upload (`POST /api/v4/documents/{id}/files/`).
- **Flexible Server Settings**: Easily configure your Mayan server IP/domain and port directly on the sign-in screen; automatically preserved in local settings.
- **Archive Search & Open**: Instant search by document number, subject, or description with double-click download and launch.
- **Zero-Dependency Deployment**: Bundles into a standalone executable with Inno Setup installer that requires no Python or system dependencies on client PCs.

---

## 🏗️ Project Structure

```text
ArchiveScanner_for_mayan_edms/
├── assets/
│   ├── logo.png               # High-resolution application logo
│   └── logo.ico               # Multi-resolution Windows app icon
├── build_assets/
│   └── .gitkeep               # Placeholder for NAPS2 portable binary
├── archive.py                 # Main application UI (scanner, form, search)
├── core.py                    # Core library & Mayan EDMS v4 REST client
├── ArchiveScannerQt.spec      # PyInstaller build specification
├── ArchiveScannerQt.iss       # Inno Setup Windows installer script
├── rthook_qt_fix.py           # PyInstaller runtime hook for fast startup
├── qt6_windows_requirements.txt # Python dependencies
├── README.md                  # English documentation
├── README_AR.md               # Arabic documentation
└── LICENSE                    # MIT License
```

---

## 🚀 Getting Started

### Prerequisites

- Windows 10 or 11 (64-bit)
- Python 3.11 or 3.12
- An active Mayan EDMS v4 instance accessible on the network

### Installation & Running from Source

1. **Clone the repository:**
   ```bash
   git clone https://github.com/bkinter17-cloud/ArchiveScanner_for_mayan_edms.git
   cd ArchiveScanner_for_mayan_edms
   ```

2. **Create and activate a virtual environment:**
   ```cmd
   python -m venv .venv
   .venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```cmd
   pip install --upgrade pip
   pip install -r qt6_windows_requirements.txt
   ```

4. **Run the app:**
   ```cmd
   python archive.py
   ```

---

## 📦 Building Standalone Executable & Installer

### 1. Setup NAPS2 Portable

Download [NAPS2 Portable](https://www.naps2.com/) and extract its contents into:
```text
build_assets\NAPS2\NAPS2.Console.exe
```

### 2. Build with PyInstaller

```cmd
.venv\Scripts\activate
pyinstaller --clean --noconfirm ArchiveScannerQt.spec
```

The output will be generated in `dist\ArchiveScanner\`.

### 3. Create Windows Installer (Optional)

Compile `ArchiveScannerQt.iss` with [Inno Setup 6](https://jrsoftware.org/isinfo.php):
```cmd
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" ArchiveScannerQt.iss
```

The setup file `DocArchiveScanner-Setup.exe` will be generated in `Output\`.

---

## ⚙️ Configuration

Server and document type settings are saved to `settings.json` (beside the EXE or in `%APPDATA%\ArchiveScanner\settings.json`).

You can also pass environment variables:
```cmd
set MAYAN_URL=http://your-server-ip:8000
set MAYAN_DOCUMENT_TYPE_ID=4
ArchiveScanner.exe
```

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
NAPS2 is licensed under the GNU LGPL.
Mayan EDMS is a registered trademark of Roberto Rosario.
