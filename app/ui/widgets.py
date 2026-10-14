"""عناصر UI المُعاد استخدامها: BrandPanel, circular_pixmap, apply_shadow, field, field_label."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (
    QFrame, QGraphicsDropShadowEffect, QLabel, QLineEdit,
    QStyle, QStyleOption, QWidget,
)

from app.utils.settings import logo_path


# ---------------------------------------------------------------------------
# أدوات الصور
# ---------------------------------------------------------------------------

def circular_pixmap(
    source_path,
    size: int,
    ring: bool = True,
    ring_color: QColor = QColor(255, 255, 255, 110),
) -> QPixmap:
    """اقتصاص صورة الشعار إلى دائرة مع حلقة توهج اختيارية."""
    source = QPixmap(str(source_path))
    if source.isNull():
        return QPixmap()
    scaled  = source.scaled(size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
    x, y    = (scaled.width() - size) // 2, (scaled.height() - size) // 2
    cropped = scaled.copy(x, y, size, size)

    result  = QPixmap(size, size)
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


# ---------------------------------------------------------------------------
# تأثير الظل
# ---------------------------------------------------------------------------

def apply_shadow(
    widget: QWidget,
    blur: int = 36,
    y_offset: int = 14,
    color: QColor | None = None,
    opacity: int = 40,
) -> None:
    """تطبيق تأثير ظل سفلي على ويدجت."""
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setOffset(0, y_offset)
    effect.setColor(color or QColor(17, 24, 39, opacity))
    widget.setGraphicsEffect(effect)


# ---------------------------------------------------------------------------
# حقول النص
# ---------------------------------------------------------------------------

def field(placeholder: str, password: bool = False) -> QLineEdit:
    """حقل نص RTL موحّد مع placeholder."""
    box = QLineEdit()
    box.setPlaceholderText(placeholder)
    box.setAlignment(Qt.AlignRight | Qt.AlignAbsolute | Qt.AlignVCenter)
    box.setLayoutDirection(Qt.RightToLeft)
    box.setMinimumHeight(42)
    if password:
        box.setEchoMode(QLineEdit.Password)
    return box


def field_label(text: str, word_wrap: bool = False) -> QLabel:
    """تسمية حقل RTL موحّدة بمحاذاة يمينية مطلقة."""
    label = QLabel(text)
    label.setObjectName("fieldLabel")
    label.setAlignment(Qt.AlignRight | Qt.AlignAbsolute | Qt.AlignVCenter)
    label.setLayoutDirection(Qt.RightToLeft)
    label.setWordWrap(word_wrap)
    return label


# ---------------------------------------------------------------------------
# BrandPanel — اللوحة الجانبية/لوحة تسجيل الدخول الداكنة
# ---------------------------------------------------------------------------

class BrandPanel(QFrame):
    """
    إطار مخصص يرسم تدرجًا لونيًا مع شعار شفاف (watermark) في الزاوية المحددة.
    """

    def __init__(
        self,
        watermark_size_ratio: float = 1.0,
        corner: str = "bottom-left",
        opacity: float = 0.07,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._watermark = None
        logo = logo_path()
        if logo:
            source = QPixmap(str(logo))
            if not source.isNull():
                self._watermark = source
        self._ratio   = watermark_size_ratio
        self._corner  = corner
        self._opacity = opacity

    def paintEvent(self, event) -> None:  # noqa: N802
        opt = QStyleOption()
        opt.initFrom(self)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        self.style().drawPrimitive(QStyle.PE_Widget, opt, painter, self)
        if self._watermark is not None and self.height() > 0:
            target = int(self.height() * self._ratio)
            scaled = self._watermark.scaled(
                target, target, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            bleed_x = int(scaled.width()  * 0.32)
            bleed_y = int(scaled.height() * 0.32)
            if self._corner == "bottom-right":
                x = self.width()  - scaled.width()  + bleed_x
                y = self.height() - scaled.height() + bleed_y
            else:
                x = -bleed_x
                y = self.height() - scaled.height() + bleed_y
            painter.setOpacity(self._opacity)
            painter.drawPixmap(x, y, scaled)
        painter.end()
