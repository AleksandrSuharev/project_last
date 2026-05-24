from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


DEFAULT_BAUD_RATE = 9600
DEFAULT_CO2_LOWER_LIMIT = 600.0
DEFAULT_CO2_UPPER_LIMIT = 1000.0
DEFAULT_TELEMETRY_INTERVAL_MS = 20000
SIMULATOR_TELEMETRY_INTERVAL_MS = 10000
MIN_WORK_SECONDS = 1
MAX_WORK_SECONDS = 86400


class WorkMode(str, Enum):
    MANUAL = "MANUAL"
    AUTO = "AUTO"

    @property
    def title(self) -> str:
        return {
            WorkMode.MANUAL: "Ручной",
            WorkMode.AUTO: "Автоматический",
        }[self]


class CommandStatus(str, Enum):
    CREATED = "CREATED"
    SENT = "SENT"
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"


class EventType(str, Enum):
    USER_ACTION = "USER_ACTION"
    COMMAND_EVENT = "COMMAND_EVENT"
    SYSTEM_EVENT = "SYSTEM_EVENT"
    ERROR_EVENT = "ERROR_EVENT"

    @property
    def title(self) -> str:
        return {
            EventType.USER_ACTION: "Действие",
            EventType.COMMAND_EVENT: "Команда",
            EventType.SYSTEM_EVENT: "Система",
            EventType.ERROR_EVENT: "Ошибка",
        }[self]


@dataclass
class ConnectionSettings:
    port_name: str = "SIMULATOR"
    baud_rate: int = DEFAULT_BAUD_RATE
    is_connected: bool = False
    use_simulator: bool = True


@dataclass
class ControlParameters:
    fan_work_time: int = 60
    device_work_time: int = 300


@dataclass
class DeviceState:
    is_enabled: bool = False
    mode: WorkMode = WorkMode.MANUAL
    status_text: str = "Ожидание подключения"


@dataclass
class FanState:
    is_enabled: bool = False
    work_time: int = 60
    last_command_name: str = ""


@dataclass
class AutoModeSettings:
    is_enabled: bool = False
    co2_lower_limit: float = DEFAULT_CO2_LOWER_LIMIT
    co2_upper_limit: float = DEFAULT_CO2_UPPER_LIMIT


@dataclass
class CO2Data:
    current_value: float = 750.0
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class CommandData:
    command_name: str
    value: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    status: CommandStatus = CommandStatus.CREATED

    @property
    def display_text(self) -> str:
        if self.value:
            return f"{self.command_name} {self.value}"
        return self.command_name


@dataclass
class LogRecord:
    timestamp: datetime
    event_type: EventType
    message: str
    command_name: str = ""
    is_successful: bool = True


@dataclass
class CO2Sample:
    timestamp: datetime
    value: float


@dataclass
class ApplicationModel:
    connection: ConnectionSettings = field(default_factory=ConnectionSettings)
    control: ControlParameters = field(default_factory=ControlParameters)
    device: DeviceState = field(default_factory=DeviceState)
    fan: FanState = field(default_factory=FanState)
    auto_mode: AutoModeSettings = field(default_factory=AutoModeSettings)
    co2_data: CO2Data = field(default_factory=CO2Data)
    log_records: list[LogRecord] = field(default_factory=list)
    co2_samples: list[CO2Sample] = field(default_factory=list)
