"""Non-blocking update checks and user-controlled installation for the Qt app."""
from pathlib import Path

from PyQt6 import QtCore, QtGui, QtWidgets

from . import updates
from .version import APP_VERSION


class UpdateTask(QtCore.QThread):
    progress = QtCore.pyqtSignal(int)

    def __init__(self, operation, parent):
        super().__init__(parent)
        self.operation = operation
        self.value = None
        self.failure = None

    def run(self):
        try:
            self.value = self.operation(self)
        except Exception as error:
            self.failure = str(error)


class UpdateController(QtCore.QObject):
    def __init__(self, owner):
        super().__init__(owner)
        self.owner = owner
        self.release = None
        self.task = None
        self.ready = None
        self.automatic = False
        self.stopping = False
        self.asset_platform = updates.platform_asset() if updates.supported_platform() else None
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(6 * 60 * 60 * 1000)
        self.timer.timeout.connect(self.check_automatically)
        owner.panel.update_button.clicked.connect(self.check_manually)

    def start(self):
        if updates.can_check_for_update():
            self.timer.start()
            QtCore.QTimer.singleShot(5000, self.check_automatically)

    def _status(self, text, busy=False):
        self.owner.panel.update_status_label.setText(text)
        self.owner.panel.update_button.setEnabled(not busy)
        if hasattr(self.owner, "update_action"):
            self.owner.update_action.setEnabled(not busy)

    def _run(self, operation, completed):
        if self.stopping or (self.task and self.task.isRunning()):
            return
        if self.task:
            self.task.deleteLater()
        self.task = UpdateTask(operation, self)
        task = self.task
        self.task.finished.connect(lambda: self.finished_task(task, completed))
        self.task.progress.connect(lambda percent: self._status(f"Baixando atualização… {percent}%", True))
        self.task.start()

    def finished_task(self, task, completed):
        if self.stopping:
            return
        if task.failure is not None:
            self.failed(task.failure)
        else:
            completed(task.value)

    def check_automatically(self):
        if self.stopping or self.release or not updates.can_check_for_update():
            return
        self.automatic = True
        self.check()

    def check_manually(self):
        if not updates.can_check_for_update():
            QtGui.QDesktopServices.openUrl(QtCore.QUrl(updates.RELEASES_URL))
            return
        self.automatic = False
        if self.release:
            self.offer_install()
        else:
            self.check()

    def check(self):
        if self.stopping or (self.task and self.task.isRunning()):
            return
        self._status("Procurando uma nova versão…", True)
        self._run(lambda task: updates.check_for_update(), self.checked)

    def checked(self, release):
        if self.stopping:
            return
        self.release = release
        if release is None:
            self._status(f"Você está com a versão atual · {APP_VERSION}")
            return
        self._status(f"Muuri {release.version} disponível. Suas preferências serão mantidas.")
        self.owner.panel.update_button.setText(f"Atualizar para {release.version}")
        self.owner.update_action.setText(f"Atualizar para {release.version}")
        if self.automatic:
            self.owner.tray_icon.showMessage("Nova versão do Muuri", f"Muuri {release.version} disponível. Clique para atualizar.",
                                              QtWidgets.QSystemTrayIcon.MessageIcon.Information, 10000)
        else:
            self.offer_install()

    def offer_install(self):
        if self.stopping or self.release is None or (self.task and self.task.isRunning()):
            return
        if not updates.can_check_for_update():
            QtGui.QDesktopServices.openUrl(QtCore.QUrl(updates.RELEASES_URL))
            return
        box = QtWidgets.QMessageBox(self.owner)
        box.setWindowTitle("Atualizar Muuri")
        box.setText(f"Atualizar o Muuri {self.release.version} agora?")
        if self.asset_platform == "macos":
            info = "O DMG será baixado e aberto no Finder. Arraste o Muuri para Aplicativos para concluir; suas preferências serão mantidas."
        else:
            info = "O aplicativo vai baixar a atualização, fechar e abrir novamente. Seus pets e preferências serão mantidos."
        box.setInformativeText(info)
        install = box.addButton("Atualizar agora", QtWidgets.QMessageBox.ButtonRole.AcceptRole)
        later = box.addButton("Mais tarde", QtWidgets.QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(later)
        box.exec()
        if box.clickedButton() != install:
            return
        self.automatic = False
        if self.ready:
            self.downloaded(self.ready)
            return
        cache = Path(QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.StandardLocation.CacheLocation)) / "updates"
        self._status("Preparando download…", True)
        self._run(lambda task: updates.download_update(self.release, cache, task.progress.emit,
                                                       task.isInterruptionRequested, self.asset_platform), self.downloaded)

    def downloaded(self, ready):
        if self.stopping:
            return
        self.ready = ready
        if self.asset_platform == "macos":
            try:
                updates.launch_macos_dmg(*ready)
            except Exception as error:
                self.failed(str(error))
                return
            self._status("DMG aberto. Arraste o Muuri para Aplicativos para concluir.")
            return
        self._status("Atualização pronta para instalar.")
        if not self.owner.panel.allow_close():
            return
        self._status("Instalando atualização…", True)
        try:
            updates.launch_installer(ready[0], ready[1], self.release.version)
        except Exception as error:
            self.failed(str(error))
            return
        self.owner.update_quit = True
        QtWidgets.QApplication.instance().quit()

    def failed(self, message):
        if self.stopping:
            return
        self._status("Falha na atualização. Tente novamente ou abra os detalhes desta mensagem.")
        self.owner.panel.update_status_label.setToolTip(message)
        if not self.automatic:
            QtWidgets.QMessageBox.warning(self.owner, "Atualização do Muuri", message)

    def shutdown(self):
        self.stopping = True
        self.timer.stop()
        if self.task and self.task.isRunning():
            self.task.requestInterruption()
            self.task.wait()
