from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from co2_control_app.controller import ApplicationController
from co2_control_app.models import DEFAULT_BAUD_RATE, MAX_WORK_SECONDS, MIN_WORK_SECONDS, LogRecord, WorkMode
from co2_control_app.ui.graph_widget import CO2GraphWidget
from co2_control_app.ui.log_window import LogWindow


class KeyboardOnlySpinBox(QSpinBox):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setButtonSymbols(QSpinBox.NoButtons)

    def wheelEvent(self, event) -> None:
        event.ignore()


class MainWindow(QMainWindow):
    def __init__(self, controller: ApplicationController) -> None:
        super().__init__()
        self.controller = controller
        self.project_dir = Path(__file__).resolve().parents[3]
        self.log_window: LogWindow | None = None

        self.setWindowTitle("Управляющая программа для экспериментальной установки очистки воздуха")
        self.resize(1180, 650)

        self._build_ui()
        self._apply_style()
        self._connect_signals()
        self._sync_fan_time_limit()
        self.refresh_ports()
        self.update_state()

    def _build_ui(self) -> None:
        central = QWidget(self)
        root = QVBoxLayout(central)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(14)

        header = QHBoxLayout()
        title = QLabel("Управляющая программа для экспериментальной установки очистки воздуха")
        title.setObjectName("Title")
        self.auto_check = QCheckBox("Автоматический режим")
        self.auto_check.setObjectName("AutoToggle")
        self.open_log_button = QPushButton("Журнал событий")
        header.addWidget(title, 1)
        header.addWidget(self.auto_check)
        header.addWidget(self.open_log_button)
        root.addLayout(header)

        top_row = QHBoxLayout()
        top_row.setSpacing(12)
        top_row.addWidget(self._create_connection_group(), 2)
        top_row.addWidget(self._create_status_group(), 3)
        root.addLayout(top_row)

        center_row = QHBoxLayout()
        center_row.setSpacing(12)
        center_row.addWidget(self._create_manual_group(), 2)
        center_row.addWidget(self._create_co2_group(), 3)
        root.addLayout(center_row, 1)

        self.setCentralWidget(central)

    def _create_connection_group(self) -> QGroupBox:
        group = QGroupBox("Подключение")
        layout = QGridLayout(group)
        layout.setColumnStretch(1, 1)

        self.simulator_check = QCheckBox("Симуляция")
        self.simulator_check.setChecked(True)

        self.port_combo = QComboBox()
        self.port_combo.setEditable(False)
        self.port_combo.setEnabled(False)

        self.refresh_ports_button = QPushButton("Обновить")
        self.refresh_ports_button.setEnabled(False)

        self.connect_button = QPushButton("Подключить")
        self.disconnect_button = QPushButton("Отключить")

        layout.addWidget(self.simulator_check, 0, 0, 1, 2)
        layout.addWidget(QLabel("COM-порт"), 1, 0)
        layout.addWidget(self.port_combo, 1, 1)
        layout.addWidget(self.refresh_ports_button, 1, 2)
        layout.addWidget(QLabel("Скорость"), 2, 0)
        layout.addWidget(QLabel(f"{DEFAULT_BAUD_RATE} бод"), 2, 1)
        layout.addWidget(self.connect_button, 3, 1)
        layout.addWidget(self.disconnect_button, 3, 2)
        return group

    def _create_status_group(self) -> QGroupBox:
        group = QGroupBox("Состояние")
        layout = QGridLayout(group)
        layout.setHorizontalSpacing(14)
        layout.setVerticalSpacing(8)

        self.connection_status = self._status_label()
        self.mode_status = self._status_label()
        self.device_status = self._status_label()
        self.fan_status = self._status_label()
        self.last_status = self._status_label()

        layout.addWidget(QLabel("Подключение"), 0, 0)
        layout.addWidget(self.connection_status, 0, 1)
        layout.addWidget(QLabel("Режим"), 0, 2)
        layout.addWidget(self.mode_status, 0, 3)
        layout.addWidget(QLabel("Установка"), 1, 0)
        layout.addWidget(self.device_status, 1, 1)
        layout.addWidget(QLabel("Вентилятор"), 1, 2)
        layout.addWidget(self.fan_status, 1, 3)
        layout.addWidget(QLabel("Последнее состояние"), 2, 0)
        layout.addWidget(self.last_status, 2, 1, 1, 3)
        return group

    def _create_manual_group(self) -> QGroupBox:
        group = QGroupBox("Ручное управление")
        layout = QGridLayout(group)
        layout.setColumnStretch(1, 1)

        self.device_time_spin = KeyboardOnlySpinBox()
        self.device_time_spin.setRange(MIN_WORK_SECONDS, MAX_WORK_SECONDS)
        self.device_time_spin.setValue(300)
        self.device_time_spin.setSuffix(" с")

        self.fan_time_spin = KeyboardOnlySpinBox()
        self.fan_time_spin.setRange(MIN_WORK_SECONDS, MAX_WORK_SECONDS)
        self.fan_time_spin.setValue(60)
        self.fan_time_spin.setSuffix(" с")

        self.set_device_time_button = QPushButton("Задать время установки")
        self.toggle_device_button = QPushButton("Запустить установку")
        self.set_fan_time_button = QPushButton("Задать время вентилятора")
        self.toggle_fan_button = QPushButton("Включить вентилятор")

        layout.addWidget(QLabel("Время установки"), 0, 0)
        layout.addWidget(self.device_time_spin, 0, 1)
        layout.addWidget(self.set_device_time_button, 0, 2)
        layout.addWidget(self.toggle_device_button, 1, 1, 1, 2)
        layout.addWidget(QLabel("Время вентилятора"), 2, 0)
        layout.addWidget(self.fan_time_spin, 2, 1)
        layout.addWidget(self.set_fan_time_button, 2, 2)
        layout.addWidget(self.toggle_fan_button, 3, 1, 1, 2)
        return group

    def _create_co2_group(self) -> QGroupBox:
        group = QGroupBox("Концентрация CO2")
        layout = QVBoxLayout(group)

        self.co2_value_label = QLabel("750 ppm")
        self.co2_value_label.setObjectName("CO2Value")
        self.co2_updated_label = QLabel("нет данных")
        self.co2_graph = CO2GraphWidget()

        layout.addWidget(self.co2_value_label)
        layout.addWidget(self.co2_updated_label)
        layout.addWidget(self.co2_graph, 1)
        return group

    def _status_label(self) -> QLabel:
        label = QLabel()
        label.setObjectName("StatusLabel")
        label.setMinimumWidth(120)
        label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        return label

    def _connect_signals(self) -> None:
        self.simulator_check.toggled.connect(self._on_simulator_toggled)
        self.refresh_ports_button.clicked.connect(self._refresh_ports_clicked)
        self.connect_button.clicked.connect(self._connect_device)
        self.disconnect_button.clicked.connect(self._disconnect_device)
        self.set_device_time_button.clicked.connect(self._set_device_time)
        self.toggle_device_button.clicked.connect(self._toggle_device)
        self.set_fan_time_button.clicked.connect(self._set_fan_time)
        self.toggle_fan_button.clicked.connect(self._toggle_fan)
        self.auto_check.toggled.connect(self._on_auto_toggled)
        self.open_log_button.clicked.connect(self._open_log_window)
        self.device_time_spin.valueChanged.connect(lambda: self._sync_fan_time_limit())

        self.controller.state_changed.connect(self.update_state)
        self.controller.log_added.connect(self.add_log_record)
        self.controller.co2_sample_added.connect(lambda sample: self.co2_graph.add_sample(sample.timestamp, sample.value))

    def refresh_ports(self) -> None:
        current = self.port_combo.currentText()
        self.port_combo.clear()
        ports = self.controller.available_ports()
        self.port_combo.addItems(ports)
        if current:
            index = self.port_combo.findText(current)
            if index >= 0:
                self.port_combo.setCurrentIndex(index)

    def update_state(self) -> None:
        model = self.controller.model
        connected = model.connection.is_connected
        manual_mode = model.device.mode == WorkMode.MANUAL
        device_stopped = not model.device.is_enabled

        self.connection_status.setText("Подключено" if connected else "Отключено")
        self.mode_status.setText(model.device.mode.title)
        self.device_status.setText("Включена" if model.device.is_enabled else "Выключена")
        self.fan_status.setText("Включен" if model.fan.is_enabled else "Выключен")
        self.last_status.setText(model.device.status_text)

        self.co2_value_label.setText(f"{model.co2_data.current_value:.0f} ppm")
        self.co2_updated_label.setText(f"обновлено: {model.co2_data.updated_at:%H:%M:%S}")

        self.connect_button.setEnabled(not connected)
        self.disconnect_button.setEnabled(connected)
        self.simulator_check.setEnabled(not connected)
        self.port_combo.setEnabled(not connected and not self.simulator_check.isChecked())
        self.refresh_ports_button.setEnabled(not connected and not self.simulator_check.isChecked())
        self.auto_check.blockSignals(True)
        self.auto_check.setChecked(model.device.mode == WorkMode.AUTO)
        self.auto_check.blockSignals(False)

        self.set_device_time_button.setEnabled(connected and device_stopped)
        self.toggle_device_button.setEnabled(connected and manual_mode)
        self.set_fan_time_button.setEnabled(connected and device_stopped)
        self.toggle_fan_button.setEnabled(connected and manual_mode and model.device.is_enabled)
        self.auto_check.setEnabled(connected and device_stopped)

        self.toggle_device_button.setText("Остановить установку" if model.device.is_enabled else "Запустить установку")
        self.toggle_fan_button.setText("Выключить вентилятор" if model.fan.is_enabled else "Включить вентилятор")

        self._set_status_color(self.connection_status, connected)
        self._set_status_color(self.device_status, model.device.is_enabled)
        self._set_status_color(self.fan_status, model.fan.is_enabled)

    def add_log_record(self, record: LogRecord) -> None:
        if self.log_window is not None:
            self.log_window.append_record(record)

    def _connect_device(self) -> None:
        use_simulator = self.simulator_check.isChecked()
        port_name = self.port_combo.currentText()
        source = "симулятор" if use_simulator else port_name
        self.controller.record_user_action(f"Нажата кнопка подключения: {source}")
        self.controller.connect_device(use_simulator=use_simulator, port_name=port_name, baud_rate=DEFAULT_BAUD_RATE)

    def _disconnect_device(self) -> None:
        self.controller.record_user_action("Нажата кнопка отключения")
        self.controller.disconnect_device()

    def _set_device_time(self) -> None:
        value = self.device_time_spin.value()
        self.controller.record_user_action(f"Введено время работы установки: {value} с")
        self.controller.set_device_work_time(value)
        self._sync_fan_time_limit()

    def _toggle_device(self) -> None:
        action = "остановки" if self.controller.model.device.is_enabled else "запуска"
        self.controller.record_user_action(f"Нажата кнопка {action} установки")
        self.controller.toggle_device()

    def _set_fan_time(self) -> None:
        value = self.fan_time_spin.value()
        self.controller.record_user_action(f"Введено время работы вентилятора: {value} с")
        self.controller.set_fan_work_time(value)

    def _toggle_fan(self) -> None:
        action = "выключения" if self.controller.model.fan.is_enabled else "включения"
        self.controller.record_user_action(f"Нажата кнопка {action} вентилятора")
        self.controller.toggle_fan()

    def _refresh_ports_clicked(self) -> None:
        self.controller.record_user_action("Нажата кнопка обновления списка COM-портов")
        self.refresh_ports()

    def _open_log_window(self) -> None:
        self.controller.record_user_action("Открыт журнал событий")
        if self.log_window is None:
            self.log_window = LogWindow(self)
            self.log_window.load_records(self.controller.model.log_records)
            self.log_window.finished.connect(self._forget_log_window)
        self.log_window.show()
        self.log_window.raise_()
        self.log_window.activateWindow()

    def _forget_log_window(self) -> None:
        self.log_window = None

    def _on_simulator_toggled(self, checked: bool) -> None:
        state = "включен" if checked else "выключен"
        self.controller.record_user_action(f"Режим симуляции {state}")
        self.port_combo.setEnabled(not checked)
        self.refresh_ports_button.setEnabled(not checked)

    def _on_auto_toggled(self, checked: bool) -> None:
        state = "включен" if checked else "выключен"
        self.controller.record_user_action(f"Автоматический режим {state}")
        self.controller.set_work_mode(WorkMode.AUTO if checked else WorkMode.MANUAL)

    def _sync_fan_time_limit(self) -> None:
        device_time = self.device_time_spin.value()
        self.fan_time_spin.setMaximum(device_time)
        if self.fan_time_spin.value() > device_time:
            self.fan_time_spin.setValue(device_time)

    def _set_status_color(self, label: QLabel, enabled: bool) -> None:
        label.setProperty("active", enabled)
        label.style().unpolish(label)
        label.style().polish(label)

    def closeEvent(self, event) -> None:
        self.controller.shutdown_and_save_report(self.project_dir)
        event.accept()

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            QWidget {
                font-family: "Segoe UI", Arial, sans-serif;
                font-size: 10pt;
                color: #1f2937;
                background: #f3f5f7;
            }
            QLabel#Title {
                font-size: 15pt;
                font-weight: 650;
                color: #111827;
                padding: 2px 0 6px 0;
            }
            QGroupBox {
                background: #ffffff;
                border: 1px solid #d9dee8;
                border-radius: 6px;
                margin-top: 14px;
                padding: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
                color: #374151;
                font-weight: 600;
            }
            QPushButton {
                background: #e9eef6;
                border: 1px solid #cdd6e3;
                border-radius: 5px;
                padding: 7px 12px;
            }
            QPushButton:hover {
                background: #dde6f2;
            }
            QPushButton:pressed {
                background: #cfdbea;
            }
            QPushButton:disabled {
                color: #9ca3af;
                background: #eef0f3;
                border-color: #e0e3e8;
            }
            QComboBox, QSpinBox {
                background: #ffffff;
                border: 1px solid #cfd6df;
                border-radius: 4px;
                padding: 5px 7px;
                min-height: 24px;
            }
            QLabel#StatusLabel {
                background: #eef0f3;
                border-radius: 4px;
                padding: 5px 8px;
                color: #4b5563;
            }
            QLabel#StatusLabel[active="true"] {
                background: #d3f9d8;
                color: #1b5e20;
            }
            QLabel#CO2Value {
                font-size: 28pt;
                font-weight: 700;
                color: #1d4ed8;
                background: transparent;
            }
            QTableWidget {
                background: #ffffff;
                border: 1px solid #d9dee8;
                gridline-color: #eef0f3;
                selection-background-color: #dbeafe;
            }
            QHeaderView::section {
                background: #edf1f6;
                border: 0;
                border-right: 1px solid #d9dee8;
                padding: 6px;
                font-weight: 600;
            }
            QCheckBox {
                spacing: 8px;
            }
            QCheckBox#AutoToggle {
                background: #ffffff;
                border: 1px solid #cdd6e3;
                border-radius: 5px;
                padding: 7px 12px;
                font-weight: 600;
            }
            QCheckBox#AutoToggle:checked {
                background: #dbeafe;
                color: #1d4ed8;
                border-color: #93c5fd;
            }
            """
        )
