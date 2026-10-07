import subprocess
import sys
import unittest
import uuid
from unittest.mock import patch

from deskpets.single_instance import SingleInstance


class SingleInstanceTests(unittest.TestCase):
    def setUp(self):
        self.name = "Local\\MuuriTest-" + uuid.uuid4().hex

    def probe(self):
        code = ("from deskpets.single_instance import SingleInstance; "
                f"lock=SingleInstance({self.name!r}); "
                "print(lock.acquire()); lock.close()")
        return subprocess.check_output([sys.executable, "-c", code], text=True).strip()

    def test_second_process_blocked_and_restart_allowed(self):
        lock = SingleInstance(self.name)
        try:
            self.assertTrue(lock.acquire())
            for _ in range(5):
                self.assertEqual(self.probe(), "False")
        finally:
            lock.close()
        self.assertEqual(self.probe(), "True")
        lock.close()

    def test_windows_releases_lock_after_forced_exit(self):
        code = ("import time; from deskpets.single_instance import SingleInstance; "
                f"lock=SingleInstance({self.name!r}); "
                "print(lock.acquire(), flush=True); time.sleep(30)")
        proc = subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.PIPE, text=True)
        try:
            self.assertEqual(proc.stdout.readline().strip(), "True")
            self.assertEqual(self.probe(), "False")
        finally:
            proc.kill()
            proc.wait(timeout=5)
            proc.stdout.close()
        self.assertEqual(self.probe(), "True")

    def test_duplicate_returns_before_creating_windows(self):
        from deskpets import main
        with patch.object(main, "SingleInstance") as factory, \
                patch.object(main.QtWidgets, "QApplication") as application, \
                patch.object(main, "MainWindow") as window:
            factory.return_value.acquire.return_value = False
            main.main()
            application.assert_not_called()
            window.assert_not_called()
            factory.return_value.close.assert_called_once()

    def test_normal_exit_releases_lock(self):
        from deskpets import main
        with patch.object(main, "SingleInstance") as factory, \
                patch.object(main.QtWidgets, "QApplication") as application, \
                patch.object(main, "MainWindow") as window:
            factory.return_value.acquire.return_value = True
            application.return_value.exec.return_value = 0
            with self.assertRaises(SystemExit):
                main.main()
            window.return_value.start_refresh.assert_called_once()
            factory.return_value.close.assert_called_once()
