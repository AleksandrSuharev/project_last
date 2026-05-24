import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from co2_control_app.controller import ApplicationController
from co2_control_app.models import SIMULATOR_TELEMETRY_INTERVAL_MS, WorkMode


class AutoModeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_auto_mode_starts_and_stops_device_by_co2_thresholds(self) -> None:
        controller = ApplicationController()
        controller.connect_device(use_simulator=True)
        self.assertEqual(controller.telemetry_timer.interval(), SIMULATOR_TELEMETRY_INTERVAL_MS)
        controller.set_work_mode(WorkMode.AUTO)

        controller.transport.co2_value = 1005.0
        controller.poll_telemetry()

        self.assertTrue(controller.model.device.is_enabled)
        self.assertFalse(controller.device_work_timer.isActive())
        self.assertFalse(controller.fan_work_timer.isActive())
        self.assertTrue(
            any("Автоматический запуск установки" in record.message for record in controller.model.log_records)
        )
        self.assertTrue(
            any("вентилятор запущен" in record.message for record in controller.model.log_records)
        )

        controller.transport.co2_value = 590.0
        controller.poll_telemetry()

        self.assertFalse(controller.model.device.is_enabled)
        self.assertTrue(
            any("Автоматическая остановка установки" in record.message for record in controller.model.log_records)
        )


if __name__ == "__main__":
    unittest.main()
