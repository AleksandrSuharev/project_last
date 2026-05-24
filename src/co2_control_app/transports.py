from __future__ import annotations

import random
import sys
from dataclasses import dataclass
from typing import Protocol

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    serial = None
    list_ports = None

from co2_control_app.models import DEFAULT_BAUD_RATE


@dataclass
class TransportResponse:
    is_successful: bool
    message: str = "OK"


class DeviceTransport(Protocol):
    def connect(self) -> TransportResponse:
        ...

    def disconnect(self) -> None:
        ...

    def send_command(self, command_name: str, value: str = "") -> TransportResponse:
        ...

    def read_co2(self) -> float | None:
        ...


class SimulatorTransport:
    def __init__(self) -> None:
        self.is_connected = False
        self.device_enabled = False
        self.fan_enabled = False
        self.fan_time = 60
        self.device_time = 300
        self.co2_value = 820.0

    def connect(self) -> TransportResponse:
        self.is_connected = True
        return TransportResponse(True, "Симулятор установки подключен")

    def disconnect(self) -> None:
        self.is_connected = False
        self.device_enabled = False
        self.fan_enabled = False

    def send_command(self, command_name: str, value: str = "") -> TransportResponse:
        if not self.is_connected:
            return TransportResponse(False, "Нет подключения к симулятору")

        try:
            if command_name == "parm_t_vent":
                self.fan_time = int(value)
            elif command_name == "vent_on":
                if not self.device_enabled:
                    return TransportResponse(False, "Вентилятор нельзя включить при выключенной установке")
                self.fan_enabled = True
            elif command_name == "vent_off":
                self.fan_enabled = False
            elif command_name == "parm_t_yct":
                self.device_time = int(value)
            elif command_name == "yct_on":
                self.device_enabled = True
                self.fan_enabled = True
            elif command_name == "yct_off":
                self.device_enabled = False
                self.fan_enabled = False
            else:
                return TransportResponse(False, f"Неизвестная команда: {command_name}")
        except ValueError:
            return TransportResponse(False, "Команда содержит некорректное числовое значение")

        return TransportResponse(True, "OK")

    def read_co2(self) -> float | None:
        if not self.is_connected:
            return None

        if self.device_enabled and self.fan_enabled:
            delta = random.uniform(28.0, 48.0)
            self.co2_value = max(520.0, self.co2_value - delta)
        else:
            delta = random.uniform(12.0, 32.0)
            self.co2_value = min(1450.0, self.co2_value + delta)

        self.co2_value += random.uniform(-8.0, 8.0)
        return round(self.co2_value, 1)


class SerialTransport:
    def __init__(
        self,
        port_name: str,
        baud_rate: int = DEFAULT_BAUD_RATE,
        timeout: float = 1.0,
    ) -> None:
        self.port_name = port_name
        self.baud_rate = baud_rate
        self.timeout = timeout
        self._serial = None

    @staticmethod
    def available_ports() -> list[str]:
        ports: list[str] = []
        if list_ports is None:
            return _windows_registry_ports()

        ports = [port.device for port in list_ports.comports()]
        if not ports:
            ports = _windows_registry_ports()
        return sorted(set(ports), key=_port_sort_key)

    def connect(self) -> TransportResponse:
        if serial is None:
            return TransportResponse(False, "Библиотека pyserial не установлена")

        try:
            self._serial = serial.Serial(
                port=self.port_name,
                baudrate=self.baud_rate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=self.timeout,
                write_timeout=self.timeout,
            )
        except serial.SerialException as error:
            return TransportResponse(False, f"Ошибка открытия COM-порта: {error}")

        return TransportResponse(True, f"Подключено к {self.port_name}")

    def disconnect(self) -> None:
        if self._serial is not None and self._serial.is_open:
            self._serial.close()

    def send_command(self, command_name: str, value: str = "") -> TransportResponse:
        if self._serial is None or not self._serial.is_open:
            return TransportResponse(False, "COM-порт не открыт")

        payload = f"{command_name} {value}\n" if value else f"{command_name}\n"

        try:
            self._serial.write(payload.encode("utf-8"))
            self._serial.flush()
            response = self._serial.readline().decode("utf-8", errors="replace").strip()
        except serial.SerialException as error:
            return TransportResponse(False, f"Ошибка обмена через COM-порт: {error}")

        if not response:
            return TransportResponse(False, "Контроллер не прислал ответ")
        if response.upper().startswith("OK"):
            return TransportResponse(True, response)
        return TransportResponse(False, response)

    def read_co2(self) -> float | None:
        if self._serial is None or not self._serial.is_open:
            return None

        try:
            while self._serial.in_waiting:
                line = self._serial.readline().decode("utf-8", errors="replace").strip()
                parsed = self._parse_co2_line(line)
                if parsed is not None:
                    return parsed
        except serial.SerialException:
            return None

        return None

    @staticmethod
    def _parse_co2_line(line: str) -> float | None:
        if not line:
            return None
        parts = line.replace("=", " ").replace(":", " ").split()
        if len(parts) < 2 or parts[0].upper() != "CO2":
            return None
        try:
            return float(parts[1])
        except ValueError:
            return None


def _windows_registry_ports() -> list[str]:
    if sys.platform != "win32":
        return []

    try:
        import winreg
    except ImportError:
        return []

    ports: list[str] = []
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DEVICEMAP\SERIALCOMM") as key:
            index = 0
            while True:
                try:
                    _, value, _ = winreg.EnumValue(key, index)
                except OSError:
                    break
                if isinstance(value, str) and value.upper().startswith("COM"):
                    ports.append(value)
                index += 1
    except OSError:
        return []

    return ports


def _port_sort_key(port_name: str) -> tuple[int, str]:
    upper_name = port_name.upper()
    if upper_name.startswith("COM"):
        number = upper_name[3:]
        if number.isdigit():
            return int(number), upper_name
    return 9999, upper_name
