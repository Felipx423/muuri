import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from PyQt6 import QtCore, QtWidgets

from deskpets import updates
from deskpets.update_controller import UpdateController


def release_data(version=None, payload=b"verified installer"):
    # Keep update fixtures newer than the app when preparing a new release.
    version = version or f"{int(updates.APP_VERSION.split('.')[0])+1}.0.0"
    tag = "muuri-v" + version
    return dict(tag_name=tag, draft=False, prerelease=False, assets=[
        dict(name=name, size=len(payload), browser_download_url=f"https://github.com/{updates.REPOSITORY}/releases/download/{tag}/{name}")
        for name in (updates.INSTALLER_NAME, "MUURI-SHA256.txt",
                     updates.MACOS_INSTALLER_NAME, updates.MACOS_CHECKSUM_NAME)])


class Response(io.BytesIO):
    def geturl(self):
        return "https://release-assets.githubusercontent.com/test"


class UpdateTests(unittest.TestCase):
    def test_only_newer_stable_releases_with_both_official_assets(self):
        self.assertEqual(updates.parse_release(release_data("1.3.0"), "1.2.0").version, "1.3.0")
        self.assertIsNone(updates.parse_release(release_data("1.2.0"), "1.2.0"))
        self.assertIsNone(updates.parse_release(release_data("1.1.1"), "1.2.0"))
        for flag in ("draft", "prerelease"):
            data = release_data()
            data[flag] = True
            self.assertIsNone(updates.parse_release(data))
        self.assertIsNone(updates.parse_release(release_data("1.3.0-macos-preview.1")))
        data = release_data()
        data["assets"].pop()
        with self.assertRaises(ValueError):
            updates.parse_release(data)

    def test_reject_foreign_asset_urls_and_invalid_sizes(self):
        for url in ("http://github.com/test.exe", "https://evil.example/Muuri-Setup.exe",
                    "https://github.com/other/repo/releases/download/muuri-v1.3.0/Muuri-Setup.exe"):
            data = release_data()
            data["assets"][0]["browser_download_url"] = url
            with self.assertRaises(ValueError):
                updates.parse_release(data)
        for size in (0, -1, True, updates.MAX_INSTALLER_BYTES+1):
            data = release_data()
            data["assets"][0]["size"] = size
            with self.assertRaises(ValueError):
                updates.parse_release(data)

    def test_checksum_requires_one_exact_installer_entry(self):
        digest = "a" * 64
        self.assertEqual(updates.installer_checksum((digest + "  Muuri-Setup.exe\n").encode()), digest)
        self.assertEqual(updates.installer_checksum((digest + " *Muuri-Setup.exe\n").encode()), digest)
        self.assertEqual(updates.asset_checksum((digest + "  Muuri-macOS-arm64.dmg\n").encode(),
                                                updates.MACOS_INSTALLER_NAME), digest)
        for text in (digest+"  another.exe", digest+"  ../Muuri-Setup.exe", "invalid", (digest+"  Muuri-Setup.exe\n")*2):
            with self.assertRaises(ValueError):
                updates.installer_checksum(text.encode())

    def test_download_validates_size_hash_and_cancel_without_touching_app(self):
        payload = b"verified installer"
        digest = hashlib.sha256(payload).hexdigest()
        manifest = (digest + "  Muuri-Setup.exe").encode()
        release = updates.parse_release(release_data(payload=payload))
        for received, cancelled, success in ((payload, False, True), (b"bad", False, False),
                                              (payload+b"extra", False, False), (payload, True, False)):
            with self.subTest(received=received, cancelled=cancelled), tempfile.TemporaryDirectory() as folder:
                with patch.object(updates, "_read_small", return_value=manifest), \
                        patch.object(updates, "urlopen", return_value=Response(received)):
                    if success:
                        path, expected = updates.download_update(release, folder)
                        self.assertEqual(path.read_bytes(), payload)
                        self.assertEqual(expected, digest)
                    else:
                        with self.assertRaises((ValueError, InterruptedError)):
                            updates.download_update(release, folder, cancelled=lambda: cancelled)
                        self.assertEqual(list(Path(folder).iterdir()), [])

    def test_macos_download_uses_dmg_and_macos_manifest(self):
        payload = b"verified dmg"
        digest = hashlib.sha256(payload).hexdigest()
        manifest = (digest + "  Muuri-macOS-arm64.dmg").encode()
        release = updates.parse_release(release_data(payload=payload))
        with tempfile.TemporaryDirectory() as folder, \
                patch.object(updates, "_read_small", return_value=manifest), \
                patch.object(updates, "urlopen", return_value=Response(payload)):
            path, expected = updates.download_update(release, folder, platform_name="macos")
            self.assertEqual(path.name, updates.MACOS_INSTALLER_NAME)
            self.assertEqual(path.read_bytes(), payload)
            self.assertEqual(expected, digest)

    def test_same_length_corruption_and_insecure_redirect_are_rejected(self):
        payload = b"verified installer"
        digest = hashlib.sha256(payload).hexdigest()
        release = updates.parse_release(release_data(payload=payload))
        with tempfile.TemporaryDirectory() as folder, \
                patch.object(updates, "_read_small", return_value=(digest+"  Muuri-Setup.exe").encode()), \
                patch.object(updates, "urlopen", return_value=Response(b"x"*len(payload))):
            with self.assertRaisesRegex(ValueError, "verificação"):
                updates.download_update(release, folder)
        response = Response()
        response.geturl = lambda: "http://release-assets.githubusercontent.com/test"
        with self.assertRaises(ValueError):
            updates._check_response(response)

    def test_installer_helper_quotes_paths_waits_and_verifies_again(self):
        with tempfile.TemporaryDirectory(prefix="Muuri's & test ") as folder:
            installer = Path(folder)/updates.INSTALLER_NAME
            installer.write_bytes(b"test")
            command = updates.installer_command(installer, "a"*64, Path(folder)/"installed app", 123)
            script = command[-1]
            self.assertIn("Wait-Process -Timeout 120", script)
            self.assertIn("System.Security.Cryptography.SHA256", script)
            self.assertNotIn("Get-FileHash", script)
            self.assertIn("/NORESTART", script)
            self.assertIn("Muuri''s & test", script)
            self.assertIn("} '", script)
            self.assertNotIn("ExecutionPolicy", " ".join(command))

    def test_installer_helper_checks_target_version(self):
        with tempfile.TemporaryDirectory() as folder:
            installer = Path(folder) / updates.INSTALLER_NAME
            installer.write_bytes(b"test")
            command = updates.installer_command(installer, "a" * 64, Path(folder) / "installed", 123, "1.4.4")
            script = command[-1]
            self.assertIn("MUURI-VERSION.txt", script)
            self.assertIn("1.4.4", script)

    def test_macos_launcher_rechecks_hash_and_opens_dmg(self):
        with tempfile.TemporaryDirectory() as folder:
            image = Path(folder) / updates.MACOS_INSTALLER_NAME
            image.write_bytes(b"dmg")
            digest = hashlib.sha256(image.read_bytes()).hexdigest()
            with patch.object(updates.sys, "platform", "darwin"), \
                    patch.object(updates.subprocess, "Popen") as popen:
                updates.launch_macos_dmg(image, digest)
            popen.assert_called_once_with(["open", str(image.resolve())], close_fds=True)

    def test_development_run_cannot_install_or_check_automatically(self):
        with patch.object(updates.sys, "frozen", False, create=True):
            self.assertFalse(updates.can_install_update())
            with self.assertRaises(RuntimeError):
                updates.launch_installer(Path("Muuri-Setup.exe"), "a"*64)


class UpdateControllerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.owner = QtWidgets.QWidget()
        self.owner.panel = SimpleNamespace(update_status_label=QtWidgets.QLabel(), update_button=QtWidgets.QPushButton())
        self.controller = UpdateController(self.owner)

    def tearDown(self):
        self.controller.shutdown()
        self.owner.deleteLater()
        self.app.processEvents()

    def test_no_network_on_source_startup_and_only_one_check_runs_at_a_time(self):
        with patch.object(updates, "can_install_update", return_value=False), \
                patch.object(updates, "check_for_update") as check:
            self.controller.start()
            self.controller.check_automatically()
            check.assert_not_called()
        loop = QtCore.QEventLoop()
        self.controller._run(lambda task: "completed", lambda result: loop.quit())
        first = self.controller.task
        self.controller._run(lambda task: self.fail("duplicate worker"), lambda result: None)
        self.assertIs(self.controller.task, first)
        QtCore.QTimer.singleShot(3000, loop.quit)
        loop.exec()
        self.assertFalse(first.isRunning())
        self.assertEqual(first.value, "completed")

    def test_download_does_not_exit_or_install_when_pending_changes_are_kept(self):
        self.owner.panel.allow_close = lambda: False
        with patch.object(updates, "launch_installer") as launch:
            self.controller.downloaded((Path("Muuri-Setup.exe"), "a"*64))
            launch.assert_not_called()
        self.assertIsNotNone(self.controller.ready)

    def test_automatic_network_failure_is_quiet_and_leaves_pets_untouched(self):
        self.controller.automatic = True
        with patch.object(QtWidgets.QMessageBox, "warning") as warning:
            self.controller.failed("offline")
            warning.assert_not_called()
        self.assertTrue(self.owner.panel.update_button.isEnabled())
        self.assertIn("Tente novamente", self.owner.panel.update_status_label.text())


if __name__ == "__main__":
    unittest.main()
