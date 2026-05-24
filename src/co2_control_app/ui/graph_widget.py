from __future__ import annotations

from collections import deque
from datetime import datetime

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

from co2_control_app.models import DEFAULT_CO2_LOWER_LIMIT, DEFAULT_CO2_UPPER_LIMIT


class CO2GraphWidget(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.samples: deque[tuple[datetime, float]] = deque(maxlen=120)
        self.setMinimumHeight(220)

    def add_sample(self, timestamp: datetime, value: float) -> None:
        self.samples.append((timestamp, value))
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#fbfcfe"))

        area = self.rect().adjusted(54, 18, -18, -38)
        painter.setPen(QPen(QColor("#d9dee8"), 1))
        painter.drawRect(area)

        values = [value for _, value in self.samples]
        y_min = min(400.0, min(values) if values else 500.0)
        y_max = max(1200.0, max(values) if values else 1100.0)
        span = max(1.0, y_max - y_min)

        self._draw_grid(painter, area, y_min, y_max)
        self._draw_threshold(painter, area, DEFAULT_CO2_LOWER_LIMIT, y_min, span, "#2f9e44", "600 ppm")
        self._draw_threshold(painter, area, DEFAULT_CO2_UPPER_LIMIT, y_min, span, "#d9480f", "1000 ppm")

        if len(self.samples) >= 2:
            path = QPainterPath()
            for index, (_, value) in enumerate(self.samples):
                x_ratio = index / max(1, len(self.samples) - 1)
                y_ratio = (value - y_min) / span
                point = QPointF(
                    area.left() + x_ratio * area.width(),
                    area.bottom() - y_ratio * area.height(),
                )
                if index == 0:
                    path.moveTo(point)
                else:
                    path.lineTo(point)
            painter.setPen(QPen(QColor("#2563eb"), 2.4))
            painter.drawPath(path)
        elif len(self.samples) == 1:
            _, value = self.samples[0]
            y_ratio = (value - y_min) / span
            point = QPointF(area.left(), area.bottom() - y_ratio * area.height())
            painter.setPen(QPen(QColor("#2563eb"), 5))
            painter.drawPoint(point)

        painter.setPen(QColor("#4b5563"))
        painter.setFont(QFont("Segoe UI", 9))
        painter.drawText(QRectF(area.left(), area.bottom() + 8, area.width(), 22), Qt.AlignCenter, "динамика CO2")

    def _draw_grid(self, painter: QPainter, area, y_min: float, y_max: float) -> None:
        painter.setFont(QFont("Segoe UI", 8))
        for step in range(5):
            ratio = step / 4
            y = area.bottom() - ratio * area.height()
            value = y_min + ratio * (y_max - y_min)
            painter.setPen(QPen(QColor("#edf0f5"), 1))
            painter.drawLine(area.left(), y, area.right(), y)
            painter.setPen(QColor("#6b7280"))
            painter.drawText(6, y + 4, f"{value:.0f}")

    def _draw_threshold(
        self,
        painter: QPainter,
        area,
        value: float,
        y_min: float,
        span: float,
        color: str,
        label: str,
    ) -> None:
        y_ratio = (value - y_min) / span
        y = area.bottom() - y_ratio * area.height()
        pen = QPen(QColor(color), 1.5)
        pen.setStyle(Qt.DashLine)
        painter.setPen(pen)
        painter.drawLine(area.left(), y, area.right(), y)
        painter.setPen(QColor(color))
        painter.setFont(QFont("Segoe UI", 8))
        painter.drawText(area.left() + 6, y - 4, label)
