from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QTimer, Signal

from co2_control_app.logger import EventLogger
from co2_control_app.models import (
    DEFAULT_BAUD_RATE,
    DEFAULT_TELEMETRY_INTERVAL_MS,
    MAX_WORK_SECONDS,
    MIN_WORK_SECONDS,
    SIMULATOR_TELEMETRY_INTERVAL_MS,
    ApplicationModel,
    CO2Sample,
    CommandData,
    CommandStatus,
    EventType,
    LogRecord,
    WorkMode,
)
from co2_control_app.transports import DeviceTransport, SerialTransport, SimulatorTransport


class ApplicationController(QObject):
    state_changed = Signal()
    log_added = Signal(object)
    co2_sample_added = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self.model = ApplicationModel()
        self.logger = EventLogger()
        self.transport: DeviceTransport | None = None

        self.telemetry_timer = QTimer(self)
        self.telemetry_timer.setInterval(DEFAULT_TELEMETRY_INTERVAL_MS)
        self.telemetry_timer.timeout.connect(self.poll_telemetry)

        self.device_work_timer = QTimer(self)
        self.device_work_timer.setSingleShot(True)
        self.device_work_timer.timeout.connect(self._stop_device_by_timer)

        self.fan_work_timer = QTimer(self)
        self.fan_work_timer.setSingleShot(True)
        self.fan_work_timer.timeout.connect(self._stop_fan_by_timer)

    def available_ports(self) -> list[str]:
        return SerialTransport.available_ports()

    def record_user_action(self, message: str) -> None:
        self._add_log(EventType.USER_ACTION, message)

    def connect_device(
        self,
        use_simulator: bool = True,
        port_name: str = "",
        baud_rate: int = DEFAULT_BAUD_RATE,
    ) -> None:
        self.disconnect_device(quiet=True)
        self.model.connection.use_simulator = use_simulator
        self.model.connection.port_name = "SIMULATOR" if use_simulator else port_name
        self.model.connection.baud_rate = baud_rate

        if use_simulator:
            self.transport = SimulatorTransport()
            self.telemetry_timer.setInterval(SIMULATOR_TELEMETRY_INTERVAL_MS)
        else:
            if not port_name:
                self._add_log(EventType.ERROR_EVENT, "COM-порт не выбран", is_successful=False)
                self.state_changed.emit()
                return
            self.transport = SerialTransport(port_name=port_name, baud_rate=baud_rate)
            self.telemetry_timer.setInterval(DEFAULT_TELEMETRY_INTERVAL_MS)

        response = self.transport.connect()
        self.model.connection.is_connected = response.is_successful
        self.model.device.status_text = response.message

        if response.is_successful:
            self.telemetry_timer.start()
            self._add_log(EventType.SYSTEM_EVENT, response.message)
        else:
            self.transport = None
            self._add_log(EventType.ERROR_EVENT, response.message, is_successful=False)

        self.state_changed.emit()

    def disconnect_device(self, quiet: bool = False) -> None:
        if self.transport is not None:
            self.transport.disconnect()

        self.telemetry_timer.stop()
        self.device_work_timer.stop()
        self.fan_work_timer.stop()
        self.transport = None
        self.model.connection.is_connected = False
        self.model.device.is_enabled = False
        self.model.fan.is_enabled = False
        self.model.auto_mode.is_enabled = False
        self.model.device.mode = WorkMode.MANUAL
        self.model.device.status_text = "Отключено"

        if not quiet:
            self._add_log(EventType.SYSTEM_EVENT, "Соединение с установкой закрыто")
            self.state_changed.emit()

    def set_work_mode(self, mode: WorkMode) -> None:
        self.model.device.mode = mode
        self.model.auto_mode.is_enabled = mode == WorkMode.AUTO
        self.state_changed.emit()

    def set_fan_work_time(self, seconds: int) -> None:
        if not self._validate_seconds(seconds, "времени работы вентилятора"):
            return
        if seconds > self.model.control.device_work_time:
            self._add_log(
                EventType.ERROR_EVENT,
                "Время работы вентилятора не может превышать время работы установки",
                is_successful=False,
            )
            self.state_changed.emit()
            return
        self.model.control.fan_work_time = seconds
        self.model.fan.work_time = seconds
        self._send_command("parm_t_vent", str(seconds), "Задано время работы вентилятора")

    def set_device_work_time(self, seconds: int) -> None:
        if not self._validate_seconds(seconds, "времени работы установки"):
            return
        self.model.control.device_work_time = seconds
        if self.model.fan.work_time > seconds:
            self.model.control.fan_work_time = seconds
            self.model.fan.work_time = seconds
            self._add_log(
                EventType.SYSTEM_EVENT,
                "Время работы вентилятора уменьшено до времени работы установки",
            )
        self._send_command("parm_t_yct", str(seconds), "Задано время работы установки")

    def toggle_device(self) -> None:
        command_name = "yct_off" if self.model.device.is_enabled else "yct_on"
        success_text = "Установка остановлена" if self.model.device.is_enabled else "Установка запущена"
        self._send_command(command_name, "", success_text)

    def toggle_fan(self) -> None:
        if not self.model.device.is_enabled:
            self._add_log(
                EventType.ERROR_EVENT,
                "Вентилятор нельзя включить при выключенной установке",
                is_successful=False,
            )
            self.state_changed.emit()
            return

        command_name = "vent_off" if self.model.fan.is_enabled else "vent_on"
        success_text = "Вентилятор выключен" if self.model.fan.is_enabled else "Вентилятор включен"
        self._send_command(command_name, "", success_text)

    def poll_telemetry(self) -> None:
        if self.transport is None or not self.model.connection.is_connected:
            return

        value = self.transport.read_co2()
        if value is None:
            return

        sample = self.logger.add_co2_sample(value)
        self.model.co2_data.current_value = value
        self.model.co2_data.updated_at = sample.timestamp
        self.model.co2_samples.append(sample)
        self.co2_sample_added.emit(sample)

        if self.model.device.mode == WorkMode.AUTO:
            self._process_auto_mode(value)

        self.state_changed.emit()

    def shutdown_and_save_report(self, project_dir: Path) -> Path:
        self._add_log(EventType.SYSTEM_EVENT, "Завершение работы приложения и сохранение отчета")
        if self.model.connection.is_connected:
            self.disconnect_device(quiet=True)
        return self.logger.save_report(project_dir / "reports")

    def _process_auto_mode(self, co2_value: float) -> None:
        lower = self.model.auto_mode.co2_lower_limit
        upper = self.model.auto_mode.co2_upper_limit

        if co2_value >= upper and not self.model.device.is_enabled:
            self._add_log(
                EventType.SYSTEM_EVENT,
                f"Автоматический режим: CO2 = {co2_value:.0f} ppm, достигнут верхний порог",
            )
            self._send_command("yct_on", "", "Автоматический запуск установки")
        elif co2_value <= lower and self.model.device.is_enabled:
            self._add_log(
                EventType.SYSTEM_EVENT,
                f"Автоматический режим: CO2 = {co2_value:.0f} ppm, достигнут нижний порог",
            )
            self._send_command("yct_off", "", "Автоматическая остановка установки")

    def _send_command(self, command_name: str, value: str, success_text: str) -> None:
        command = CommandData(command_name=command_name, value=value)

        if self.transport is None or not self.model.connection.is_connected:
            command.status = CommandStatus.ERROR
            self._add_log(
                EventType.ERROR_EVENT,
                "Команда не отправлена: нет подключения к установке",
                command_name=command.command_name,
                is_successful=False,
            )
            self.state_changed.emit()
            return

        command.status = CommandStatus.SENT
        response = self.transport.send_command(command.command_name, command.value)

        if response.is_successful:
            command.status = CommandStatus.SUCCESS
            self._apply_successful_command(command)
            self.model.device.status_text = success_text
            self._add_log(
                EventType.COMMAND_EVENT,
                success_text,
                command_name=command.command_name,
            )
        else:
            command.status = CommandStatus.ERROR
            self._handle_connection_error(response.message, command.command_name)

        self.state_changed.emit()

    def _apply_successful_command(self, command: CommandData) -> None:
        if command.command_name == "yct_on":
            self.model.device.is_enabled = True
            self.model.fan.is_enabled = True
            if self.model.device.mode == WorkMode.AUTO:
                self._add_log(
                    EventType.SYSTEM_EVENT,
                    "Автоматический режим: вентилятор запущен вместе с установкой",
                    command_name=command.command_name,
                )
            if self.model.device.mode == WorkMode.MANUAL:
                self.device_work_timer.start(self.model.control.device_work_time * 1000)
                self.fan_work_timer.start(self.model.fan.work_time * 1000)
        elif command.command_name == "yct_off":
            self.model.device.is_enabled = False
            self.model.fan.is_enabled = False
            self.device_work_timer.stop()
            self.fan_work_timer.stop()
        elif command.command_name == "vent_on":
            self.model.fan.is_enabled = True
            self.fan_work_timer.start(self.model.fan.work_time * 1000)
        elif command.command_name == "vent_off":
            self.model.fan.is_enabled = False
            self.fan_work_timer.stop()
        elif command.command_name == "parm_t_vent":
            self.model.fan.last_command_name = command.command_name

    def _handle_connection_error(self, message: str, command_name: str = "") -> None:
        self._add_log(
            EventType.ERROR_EVENT,
            message,
            command_name=command_name,
            is_successful=False,
        )

        if self.model.device.is_enabled or self.model.auto_mode.is_enabled:
            self.model.device.is_enabled = False
            self.model.fan.is_enabled = False
            self.model.auto_mode.is_enabled = False
            self.model.device.mode = WorkMode.MANUAL
            self.model.device.status_text = "Работа остановлена из-за ошибки обмена"
            self.telemetry_timer.stop()
            self.device_work_timer.stop()
            self.fan_work_timer.stop()

    def _validate_seconds(self, value: int, field_name: str) -> bool:
        if MIN_WORK_SECONDS <= value <= MAX_WORK_SECONDS:
            return True

        self._add_log(
            EventType.ERROR_EVENT,
            f"Некорректное значение {field_name}: допустимо от {MIN_WORK_SECONDS} до {MAX_WORK_SECONDS} секунд",
            is_successful=False,
        )
        self.state_changed.emit()
        return False

    def _add_log(
        self,
        event_type: EventType,
        message: str,
        command_name: str = "",
        is_successful: bool = True,
    ) -> LogRecord:
        record = self.logger.add(event_type, message, command_name, is_successful)
        self.model.log_records.append(record)
        self.log_added.emit(record)
        return record

    def _stop_device_by_timer(self) -> None:
        if self.model.device.mode == WorkMode.AUTO:
            return

        if self.model.device.is_enabled:
            self._add_log(EventType.SYSTEM_EVENT, "Истекло заданное время работы установки")
            self._send_command("yct_off", "", "Установка остановлена по заданному времени")

    def _stop_fan_by_timer(self) -> None:
        if self.model.device.mode == WorkMode.AUTO:
            return

        if self.model.fan.is_enabled:
            self._add_log(EventType.SYSTEM_EVENT, "Истекло заданное время работы вентилятора")
            self._send_command("vent_off", "", "Вентилятор остановлен по заданному времени")
