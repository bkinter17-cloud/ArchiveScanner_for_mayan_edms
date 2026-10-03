# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

project = Path(SPECPATH)
naps2 = project / "build_assets" / "NAPS2"
assets = project / "assets"
rthook = project / "rthook_qt_fix.py"

datas, binaries, hiddenimports = [], [], []
if naps2.exists():
    datas.append((str(naps2), "NAPS2"))
for asset_name in ("logo.png", "logo.ico"):
    asset = assets / asset_name
    if asset.exists():
        datas.append((str(asset), "assets"))

# Python-level modules to exclude (removes their .pyd and some DLL deps)
UNUSED_QT_MODULES = [
    "PySide6.Qt3DAnimation", "PySide6.Qt3DCore", "PySide6.Qt3DExtras",
    "PySide6.Qt3DInput", "PySide6.Qt3DLogic", "PySide6.Qt3DRender",
    "PySide6.QtAxContainer", "PySide6.QtBluetooth", "PySide6.QtCharts",
    "PySide6.QtDataVisualization", "PySide6.QtDesigner",
    "PySide6.QtHelp", "PySide6.QtLocation",
    "PySide6.QtMultimedia", "PySide6.QtMultimediaWidgets",
    "PySide6.QtNfc", "PySide6.QtOpenGL", "PySide6.QtOpenGLWidgets",
    "PySide6.QtPdf", "PySide6.QtPdfWidgets",
    "PySide6.QtPositioning", "PySide6.QtPrintSupport",
    "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtQuickControls2",
    "PySide6.QtQuickWidgets", "PySide6.QtRemoteObjects",
    "PySide6.QtScxml", "PySide6.QtSensors", "PySide6.QtSerialBus",
    "PySide6.QtSerialPort", "PySide6.QtSpatialAudio",
    "PySide6.QtSql", "PySide6.QtStateMachine",
    "PySide6.QtTest", "PySide6.QtTextToSpeech",
    "PySide6.QtUiTools", "PySide6.QtVirtualKeyboard",
    "PySide6.QtWebChannel", "PySide6.QtWebEngine",
    "PySide6.QtWebEngineCore", "PySide6.QtWebEngineQuick",
    "PySide6.QtWebEngineWidgets", "PySide6.QtWebSockets",
    "PySide6.QtXml",
]

# DLL names that the PySide6 hook copies even when the module is excluded.
# These are the main culprits for the black-window delay on Windows:
#   Qt6VirtualKeyboard — initialises an IME subsystem before the first paint
#   Qt6Qml / Qt6Quick / Qt6QmlModels / Qt6QmlWorkerScript — QML engine
#   Qt6Pdf — PDF renderer (not used by this app)
#   opengl32sw — software OpenGL fallback (~20 MB, unused on modern Windows)
REMOVE_DLLS = {
    "qt6virtualkeyboard.dll",
    "qt6qml.dll",
    "qt6qmlmeta.dll",
    "qt6qmlmodels.dll",
    "qt6qmlworkerscript.dll",
    "qt6quick.dll",
    "qt6pdf.dll",
    "opengl32sw.dll",
}

analysis = Analysis(
    [str(project / "archive.py")],
    pathex=[str(project)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[str(rthook)],
    excludes=UNUSED_QT_MODULES,
    noarchive=False,
)

# Strip the unwanted DLLs from the collected binaries list.
# PyInstaller stores each entry as (dest_path, src_path, type_tag).
analysis.binaries = [
    (dest, src, kind)
    for dest, src, kind in analysis.binaries
    if Path(dest).name.lower() not in REMOVE_DLLS
]

pyz = PYZ(analysis.pure)
app_icon = project / "assets" / "logo.ico"
exe = EXE(
    pyz, analysis.scripts, analysis.binaries, analysis.datas, [],
    name="ArchiveScanner",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    exclude_binaries=True,
    icon=str(app_icon) if app_icon.exists() else None,
)

COLLECT(
    exe,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=True,
    name="ArchiveScanner",
)
