from __future__ import annotations

from datetime import datetime
from pathlib import Path

from co2_control_app.models import CO2Sample, EventType, LogRecord


class EventLogger:
    def __init__(self) -> None:
        self.records: list[LogRecord] = []
        self.co2_samples: list[CO2Sample] = []

    def add(
        self,
        event_type: EventType,
        message: str,
        command_name: str = "",
        is_successful: bool = True,
    ) -> LogRecord:
        record = LogRecord(
            timestamp=datetime.now(),
            event_type=event_type,
            message=message,
            command_name=command_name,
            is_successful=is_successful,
        )
        self.records.append(record)
        return record

    def add_co2_sample(self, value: float) -> CO2Sample:
        sample = CO2Sample(timestamp=datetime.now(), value=value)
        self.co2_samples.append(sample)
        return sample

    def save_report(self, reports_dir: Path) -> Path:
        reports_dir.mkdir(parents=True, exist_ok=True)
        created_at = datetime.now()
        path = reports_dir / f"report_{created_at:%Y%m%d_%H%M%S}.txt"

        lines: list[str] = [
            "Отчет управляющей программы экспериментальной установки очистки воздуха",
            f"Дата формирования: {created_at:%Y-%m-%d %H:%M:%S}",
            "",
            "Журнал событий",
            "--------------",
        ]

        if self.records:
            for record in self.records:
                result = "успешно" if record.is_successful else "ошибка"
                command = record.command_name if record.command_name else "-"
                lines.append(
                    f"{record.timestamp:%Y-%m-%d %H:%M:%S} | "
                    f"{record.event_type.title} | {result} | {command} | {record.message}"
                )
        else:
            lines.append("События отсутствуют.")

        lines.extend(["", "Измерения CO2", "-------------"])

        if self.co2_samples:
            for sample in self.co2_samples:
                lines.append(f"{sample.timestamp:%Y-%m-%d %H:%M:%S} | {sample.value:.0f} ppm")
        else:
            lines.append("Измерения отсутствуют.")

        path.write_text("\n".join(lines), encoding="utf-8")
        return path
