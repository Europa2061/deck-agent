import logging
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend import logging_setup


class LoggingTests(unittest.TestCase):
    def setUp(self):
        logging_setup._secrets.clear()
        logging_setup._log_dir = None
        self._detach()

    def tearDown(self):
        self._detach()
        logging_setup._secrets.clear()
        logging_setup._log_dir = None

    @staticmethod
    def _detach():
        logger = logging.getLogger(logging_setup.LOGGER_NAME)
        for handler in list(logger.handlers):
            if getattr(handler, "deck_agent_file", False):
                logger.removeHandler(handler)
                handler.close()

    def _path(self, directory):
        return Path(directory) / logging_setup.LOG_FILENAME

    def test_key_events_survive_strict_root_level_and_carry_pid_and_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = logging.getLogger()
            previous = root.level
            root.setLevel(logging.ERROR)
            try:
                logging_setup.setup_logging(tmp, debug=False)
                logging_setup.logger_for("abcdef12-3456-7890").info("任务开始 provider=test")
            finally:
                root.setLevel(previous)
            path = self._path(tmp)
            text = path.read_text(encoding="utf-8")
            self.assertIn("任务开始 provider=test", text)
            self.assertIn("session=abcdef12", text)
            self.assertIn(f"pid={os.getpid()}", text)
            self.assertIn(" INFO  ", text)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_extra_logger_records_land_in_file_without_changing_its_level(self):
        extra = logging.getLogger("deck_agent_extra_test")
        extra.setLevel(logging.INFO)
        with tempfile.TemporaryDirectory() as tmp:
            try:
                logging_setup.setup_logging(tmp, debug=True, extra_logger=extra)
                extra.info("Decky 自身记录")
            finally:
                for item in list(extra.handlers):
                    if getattr(item, "deck_agent_file", False):
                        extra.removeHandler(item)
                        item.close()
            text = self._path(tmp).read_text(encoding="utf-8")
            self.assertIn("Decky 自身记录", text)
            self.assertIn("session=-", text)
            self.assertEqual(extra.level, logging.INFO)

    def test_debug_details_only_when_debug_enabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            logging_setup.setup_logging(tmp, debug=False)
            logging_setup.logger_for().debug("细节请求")
            self.assertNotIn("细节请求", self._path(tmp).read_text(encoding="utf-8"))

            logging_setup.setup_logging(tmp, debug=True)
            logging_setup.logger_for().debug("细节请求")
            self.assertIn("细节请求", self._path(tmp).read_text(encoding="utf-8"))

    def test_secret_values_are_redacted_including_tracebacks(self):
        with tempfile.TemporaryDirectory() as tmp:
            logging_setup.register_secret("sk-live-1234567890")
            log = logging_setup.setup_logging(tmp, debug=False)
            log.info("请求使用 sk-live-1234567890 发出")
            log = logging_setup.logger_for()
            try:
                raise RuntimeError("upstream rejected sk-live-1234567890")
            except RuntimeError:
                log.exception("模型请求失败")
            text = self._path(tmp).read_text(encoding="utf-8")
            self.assertNotIn("sk-live-1234567890", text)
            self.assertIn("[已隐藏]", text)
            self.assertIn("Traceback", text)

    def test_rotation_keeps_at_most_three_bounded_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = logging_setup.setup_logging(tmp, debug=False)
            payload = "写盘测试" + "x" * 900
            for _ in range(13000):
                log.info("%s", payload)
            files = sorted(Path(tmp).glob(logging_setup.LOG_FILENAME + "*"))
            self.assertLessEqual(len(files), logging_setup.BACKUP_COUNT + 1)
            for path in files:
                self.assertLessEqual(path.stat().st_size, logging_setup.MAX_BYTES)
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_debug_enabled_reads_env_and_marker_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertFalse(logging_setup.debug_enabled(tmp))
            with patch.dict(os.environ, {"DECK_AGENT_DEBUG": "1"}):
                self.assertTrue(logging_setup.debug_enabled(tmp))
            with patch.dict(os.environ, {"DECK_AGENT_DEBUG": ""}):
                self.assertFalse(logging_setup.debug_enabled(tmp))
                (Path(tmp) / logging_setup.DEBUG_MARKER).write_text("")
                self.assertTrue(logging_setup.debug_enabled(tmp))

    def test_recent_errors_reads_warnings_and_errors_from_disk(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = logging_setup.setup_logging(tmp, debug=False)
            log.warning("第一处警告")
            log.error("第一处错误")
            log.info("普通记录")
            errors = logging_setup.recent_errors()
            self.assertTrue(any("第一处警告" in line for line in errors))
            self.assertTrue(any("第一处错误" in line for line in errors))
            self.assertFalse(any("普通记录" in line for line in errors))
            files = logging_setup.log_files()
            self.assertEqual(files[0]["name"], logging_setup.LOG_FILENAME)


if __name__ == "__main__":
    unittest.main()
