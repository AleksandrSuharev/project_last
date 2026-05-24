from __future__ import annotations

from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDialog,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from co2_control_app.models import LogRecord


class LogWindow(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Журнал событий")
        self.resize(980, 520)

        layout = QVBoxLayout(self)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Время", "Тип", "Сообщение", "Команда", "Результат"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

    def load_records(self, records: list[LogRecord]) -> None:
        self.table.setRowCount(0)
        for record in records:
            self.append_record(record)

    def append_record(self, record: LogRecord) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)
        values = [
            record.timestamp.strftime("%H:%M:%S"),
            record.event_type.title,
            record.message,
            record.command_name or "-",
            "успешно" if record.is_successful else "ошибка",
        ]
        for column, value in enumerate(values):
            item = QTableWidgetItem(value)
            if column == 4:
                item.setForeground(QColor("#2f9e44" if record.is_successful else "#c92a2a"))
            self.table.setItem(row, column, item)
        self.table.scrollToBottom()
