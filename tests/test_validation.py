import unittest

from co2_control_app.models import MAX_WORK_SECONDS, MIN_WORK_SECONDS


class ValidationRangeTest(unittest.TestCase):
    def test_work_time_range_is_positive_and_bounded(self) -> None:
        self.assertEqual(MIN_WORK_SECONDS, 1)
        self.assertEqual(MAX_WORK_SECONDS, 86400)
        self.assertLess(MIN_WORK_SECONDS, MAX_WORK_SECONDS)


if __name__ == "__main__":
    unittest.main()
