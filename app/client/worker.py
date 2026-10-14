"""Worker — QThread مساعد لتشغيل العمليات الثقيلة خارج الخيط الرئيسي."""
from __future__ import annotations

from typing import Callable, Any

from PySide6.QtCore import QThread, Signal


class Worker(QThread):
    """
    يُنفّذ دالة callable في خيط منفصل.
    يُرسل إشارة `finished` بالنتيجة أو `failed` برسالة الخطأ.
    """
    finished: Signal = Signal(object)
    failed:   Signal = Signal(str)

    def __init__(
        self,
        function: Callable[..., Any],
        *args: Any,
        parent: Any = None,
    ) -> None:
        super().__init__(parent)
        self.function = function
        self.args     = args

    def run(self) -> None:
        try:
            self.finished.emit(self.function(*self.args))
        except Exception as error:
            self.failed.emit(str(error))
