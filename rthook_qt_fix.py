"""PyInstaller runtime hook — sets Qt environment variables to prevent the
black-window flash on Windows before the first Qt frame is painted.
This file is executed inside the frozen process before any app code runs."""
import os
import sys

# Disable Qt's virtual keyboard (causes a black-window delay on Windows)
os.environ.setdefault("QT_IM_MODULE", "")

# Force native Windows platform plugin (avoids OpenGL init delay)
os.environ.setdefault("QT_QPA_PLATFORM", "windows")

# Disable High-DPI fractional scaling quirks that can cause a blank frame
os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")

# Tell Qt where its platform plugins live (beside the EXE in _internal/PySide6/plugins)
if getattr(sys, "frozen", False):
    import pathlib
    meipass = pathlib.Path(sys._MEIPASS)
    plugin_path = meipass / "PySide6" / "plugins"
    if plugin_path.exists():
        os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = str(plugin_path)
