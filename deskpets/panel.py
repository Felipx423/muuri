import copy
import html
import time

from PIL import Image
from PyQt6 import QtCore, QtGui, QtWidgets

from . import config_io
from .pets import PETS_DATA


SIZES = [("Very Small", "Bem pequeno", 20), ("Small", "Pequeno", 40),
         ("Original", "Original", None), ("Medium", "Médio", 125),
         ("Big", "Grande", 150), ("Really Big", "Bem grande", 200)]
STATE_NAMES = {"idle": "Parada", "walk": "Andando", "walk_fast": "Trotando",
               "run": "Correndo", "lie": "Descansando", "swipe": "Reação",
               "drag": "Sendo arrastada", "fly": "Voando"}
FIELDS = ("enabled", "colors", "size", "draggable", "physics_enabled", "movement_multiplier", "animation_multiplier")
STYLE = """
QWidget { color: #223957; font-family: 'Segoe UI'; font-size: 13px; }
QWidget#panel { background: #f4f8fd; }
QLabel#brand { font-size: 25px; font-weight: 700; color: #124f9c; }
QLabel#title { font-size: 23px; font-weight: 700; }
QLabel#muted { color: #61758e; }
QFrame#card { background: white; border: 1px solid #dce6f2; border-radius: 12px; }
QTabWidget::pane { border: 0; }
QScrollArea { border: 0; background: transparent; }
QWidget#petsContent { background: #f4f8fd; }
QTabBar::tab { padding: 10px 24px; margin: 0 6px 12px 0; border-radius: 7px; }
QTabBar::tab:selected { background: #dcecff; color: #1257a6; font-weight: 600; }
QListWidget { background: white; border: 1px solid #dce6f2; border-radius: 10px; padding: 6px; }
QListWidget::item { padding: 9px; border-radius: 6px; }
QListWidget::item:selected { background: #e5f0ff; color: #1458a5; }
QComboBox { background: white; border: 1px solid #b9cce3; border-radius: 6px; padding: 6px; min-height: 20px; }
QComboBox QAbstractItemView { background: white; selection-background-color: #dcecff; selection-color: #223957; }
QPushButton { background: white; border: 1px solid #b9cce3; border-radius: 7px; padding: 9px 16px; }
QPushButton:hover { background: #edf5ff; }
QPushButton#primary { background: #1769c8; color: white; border: 0; font-weight: 600; }
QPushButton#primary:disabled { background: #e1e8f1; color: #8191a5; }
QPushButton:disabled { background: #e1e8f1; color: #8191a5; }
QCheckBox { spacing: 8px; padding: 4px 0; }
QSlider::groove:horizontal { background: #dce6f2; height: 5px; border-radius: 2px; }
QSlider::sub-page:horizontal { background: #4389dd; }
QSlider::handle:horizontal { background: #1769c8; width: 15px; margin: -5px 0; border-radius: 7px; }
QTextBrowser { background: white; border: 1px solid #dce6f2; border-radius: 10px; padding: 14px; }
"""


def label(text, name=None):
    widget = QtWidgets.QLabel(text)
    if name:
        widget.setObjectName(name)
    widget.setWordWrap(True)
    return widget


class Preview(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(270, 210)
        self.frames = []
        self.cache = {}
        self.frame_index = 0
        self.offset = 0
        self.last_tick = time.monotonic()
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(16)
        self.timer.timeout.connect(self.advance)
        self.timer.start()

    def configure(self, species, color, state, size, fps, movement, animation, direction):
        data = PETS_DATA[species]
        path = data["states"][color][state]
        if path not in self.cache:
            with Image.open(config_io.BASE_DIR / path) as gif:
                frames = []
                for index in range(gif.n_frames):
                    gif.seek(index)
                    frames.append(gif.convert("RGBA"))
            self.cache[path] = frames
        originals = self.cache[path]
        height = next(h for key, _, h in SIZES if key == size) or originals[0].height
        width = int(originals[0].width * height / originals[0].height)
        self.frames = []
        for frame in originals:
            frame = frame.resize((width, height), Image.Resampling.LANCZOS)
            raw = frame.tobytes()
            self.frames.append(QtGui.QImage(raw, width, height, width * 4,
                               QtGui.QImage.Format.Format_RGBA8888).copy())
        defaults = data.get("defaults", {}).get(state, {})
        self.fps = fps * defaults.get("speed_animation", 1.0) * animation
        self.velocity = defaults.get("movement_speed", 0) * fps * defaults.get("speed_animation", 1.0) * movement
        self.direction = direction
        self.frame_index = 0
        self.offset = 0
        self.last_tick = time.monotonic()
        self.update()

    def advance(self):
        now = time.monotonic()
        elapsed = min(now - self.last_tick, 0.25)
        self.last_tick = now
        if self.frames:
            self.frame_index = (self.frame_index + elapsed * self.fps) % len(self.frames)
            scale = self.display_scale()
            span = max(1, self.width() - self.frames[0].width() * scale - 24)
            self.offset = (self.offset + elapsed * self.velocity * scale) % span
            self.update()

    def display_scale(self):
        return min(2, (self.width()-24)/self.frames[0].width(),
                   (self.height()-24)/self.frames[0].height())

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setClipRect(self.rect())
        for y in range(0, self.height(), 16):
            for x in range(0, self.width(), 16):
                painter.fillRect(x, y, 16, 16, QtGui.QColor("#eaf0f7" if (x//16+y//16)%2 else "#f8faff"))
        if not self.frames:
            return
        frame = self.frames[int(self.frame_index)]
        if self.direction < 0:
            frame = frame.mirrored(True, False)
        scale = self.display_scale()
        width, height = frame.width()*scale, frame.height()*scale
        span = max(0, self.width()-width-24)
        x = (self.width()-width)//2 if not self.velocity else 12 + (self.offset if self.direction > 0 else span-self.offset)
        y = (self.height()-height)//2
        painter.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform)
        painter.drawImage(QtCore.QRectF(x, y, width, height), frame)


class SettingsPanel(QtWidgets.QWidget):
    def __init__(self, owner):
        super().__init__()
        self.owner = owner
        self.loading = True
        self.selecting = False
        self.setObjectName("panel")
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(STYLE)
        self.original = config_io.read_json(config_io.LIST_FILE)
        self.config = config_io.read_json(config_io.CONFIG_FILE)
        self.draft = copy.deepcopy(self.original)
        self.layer = self.config.get("layer", "front")
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(24, 18, 24, 18)
        outer.setSpacing(12)
        outer.addWidget(label("Muuri", "brand"))
        outer.addWidget(label("Selecione um pet na lista e clique em Aplicar para trocar seu companheiro.", "muted"))
        self.tabs = QtWidgets.QTabWidget()
        outer.addWidget(self.tabs, 1)
        pets_page = QtWidgets.QWidget()
        pets_page.setObjectName("petsContent")
        pets_page.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)
        pets_layout = QtWidgets.QHBoxLayout(pets_page)
        pets_layout.setSizeConstraint(QtWidgets.QLayout.SizeConstraint.SetMinimumSize)
        pets_layout.setContentsMargins(0, 0, 0, 0)
        pets_layout.setSpacing(16)
        self.species_list = QtWidgets.QListWidget()
        self.species_list.setFixedWidth(170)
        for species in sorted(PETS_DATA, key=lambda name: (name != "muuri", name)):
            item = QtWidgets.QListWidgetItem(species.capitalize())
            item.setData(QtCore.Qt.ItemDataRole.UserRole, species)
            self.species_list.addItem(item)
        pets_layout.addWidget(self.species_list)
        controls = QtWidgets.QFrame()
        controls.setObjectName("card")
        controls.setMinimumWidth(260)
        form = QtWidgets.QVBoxLayout(controls)
        form.setContentsMargins(18, 16, 18, 16)
        form.setSpacing(9)
        self.title = label("", "title")
        form.addWidget(self.title)
        self.enabled = QtWidgets.QCheckBox("Mostrar na área de trabalho")
        form.addWidget(self.enabled)
        form.addWidget(label("Cores"))
        self.colors_box = QtWidgets.QWidget()
        self.colors_layout = QtWidgets.QGridLayout(self.colors_box)
        self.colors_layout.setContentsMargins(0, 0, 0, 0)
        form.addWidget(self.colors_box)
        form.addWidget(label("Tamanho"))
        self.size = QtWidgets.QComboBox()
        form.addWidget(self.size)
        self.draggable = QtWidgets.QCheckBox("Permitir arrastar com o mouse")
        form.addWidget(self.draggable)
        self.physics = QtWidgets.QCheckBox("Ativar física")
        self.physics.setToolTip("Ligada: gravidade, arremesso e quique leve. Desligada: o pet permanece onde você o soltar.")
        form.addWidget(self.physics)
        self.movement, self.movement_value = self.add_speed(form, "Velocidade de movimento")
        self.animation, self.animation_value = self.add_speed(form, "Velocidade da animação")
        form.addWidget(label("1× mantém a velocidade original.\nA animação não altera a duração dos estados.", "muted"))
        form.addStretch()
        pets_layout.addWidget(controls, 1)
        preview_card = QtWidgets.QFrame()
        preview_card.setObjectName("card")
        preview_layout = QtWidgets.QVBoxLayout(preview_card)
        preview_layout.setContentsMargins(16, 16, 16, 16)
        preview_layout.addWidget(label("Prévia", "title"))
        preview_layout.addWidget(label("Experimente antes de aplicar", "muted"))
        self.preview = Preview()
        preview_layout.addWidget(self.preview, 1)
        self.preview_info = label("", "muted")
        preview_layout.addWidget(self.preview_info)
        self.preview_color = QtWidgets.QComboBox()
        self.preview_state = QtWidgets.QComboBox()
        self.preview_direction = QtWidgets.QComboBox()
        self.preview_direction.addItem("Para a direita", 1)
        self.preview_direction.addItem("Para a esquerda", -1)
        for text, widget in (("Cor da prévia", self.preview_color), ("Animação", self.preview_state),
                             ("Direção", self.preview_direction)):
            preview_layout.addWidget(label(text))
            preview_layout.addWidget(widget)
        pets_layout.addWidget(preview_card, 1)
        self.pets_scroll = QtWidgets.QScrollArea()
        self.pets_scroll.setWidgetResizable(True)
        self.pets_scroll.setWidget(pets_page)
        self.tabs.addTab(self.pets_scroll, "Pets")
        preferences = QtWidgets.QWidget()
        pref = QtWidgets.QVBoxLayout(preferences)
        pref.addWidget(label("Preferências", "title"))
        pref.addWidget(label("Posição dos pets em relação às outras janelas"))
        self.layer_combo = QtWidgets.QComboBox()
        self.layer_combo.addItem("Na frente das outras janelas", "front")
        self.layer_combo.addItem("Atrás das outras janelas", "back")
        self.layer_combo.setCurrentIndex(max(0, self.layer_combo.findData(self.layer)))
        pref.addWidget(self.layer_combo)
        pref.addSpacing(18)
        pref.addWidget(label("Quatro cliques na Muuri abrem este painel", "title"))
        pref.addWidget(label("Clique quatro vezes em até 1,5 segundo, sem arrastar. Funciona mesmo com o arraste desligado.\n\nFechar o painel mantém os pets ativos. Use Sair na bandeja para encerrar.", "muted"))
        pref.addStretch()
        self.tabs.addTab(preferences, "Preferências")
        credits = QtWidgets.QTextBrowser()
        credits.setOpenExternalLinks(True)
        license_path = config_io.BASE_DIR.parent / "LICENSE"
        license_text = license_path.read_text(encoding="utf-8") if license_path.exists() else "Consulte LICENSE na distribuição original."
        credits.setHtml('<h2>Créditos e licença</h2><p>DeskPets por Minniti Julien (Jumitti).</p>'
                        '<p><a href="https://github.com/Jumitti/DeskPets">Projeto original</a> · '
                        '<a href="https://github.com/Jumitti/DeskPets#credits">Créditos originais</a></p>'
                        '<p>Inspirado em <a href="https://github.com/tonybaloney/vscode-pets">vscode-pets</a>, '
                        'por tonybaloney. As mídias originais vêm desse projeto e seus créditos continuam aplicáveis.</p>'
                        '<p>Muuri: design de referência fornecido pelo usuário; animações adaptadas para DeskPets.</p>'
                        '<h3>Licença MIT do DeskPets</h3><pre style="white-space: pre-wrap">'
                        + html.escape(license_text) + '</pre>')
        self.tabs.addTab(credits, "Créditos")
        footer = QtWidgets.QHBoxLayout()
        self.status = label("", "muted")
        footer.addWidget(self.status, 1)
        self.discard_button = QtWidgets.QPushButton("Descartar alterações")
        self.apply_button = QtWidgets.QPushButton("Aplicar")
        self.apply_button.setObjectName("primary")
        footer.addWidget(self.discard_button)
        footer.addWidget(self.apply_button)
        outer.addLayout(footer)
        self.enabled.toggled.connect(self.changed)
        self.draggable.toggled.connect(self.changed)
        self.physics.toggled.connect(self.changed)
        self.size.currentIndexChanged.connect(self.changed)
        self.movement.valueChanged.connect(self.changed)
        self.animation.valueChanged.connect(self.changed)
        self.layer_combo.currentIndexChanged.connect(self.layer_changed)
        self.preview_color.currentIndexChanged.connect(self.color_preview_changed)
        self.preview_state.currentIndexChanged.connect(self.update_preview)
        self.preview_direction.currentIndexChanged.connect(self.update_preview)
        self.species_list.currentItemChanged.connect(self.selection_changed)
        self.species_list.itemClicked.connect(self.activate_selected)
        self.discard_button.clicked.connect(self.discard)
        self.apply_button.clicked.connect(self.apply)
        self.loading = False
        self.select("muuri")

    def add_speed(self, layout, text):
        row = QtWidgets.QHBoxLayout()
        row.addWidget(label(text), 1)
        value = label("1,00×")
        row.addWidget(value)
        layout.addLayout(row)
        slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        slider.setRange(50, 200)
        slider.setSingleStep(5)
        slider.setPageStep(10)
        slider.setAccessibleName(text)
        layout.addWidget(slider)
        return slider, value

    def entry(self):
        return next((e for e in self.draft["pets"] if e["species"] == self.species),
                    {"species": self.species, "colors": [], "enabled": False, "size": "Original"})

    def select(self, species):
        # Opening the panel or selecting a pet programmatically must not stage a swap.
        self.selecting = True
        try:
            for index in range(self.species_list.count()):
                if self.species_list.item(index).data(QtCore.Qt.ItemDataRole.UserRole) == species:
                    self.species_list.setCurrentRow(index)
                    break
        finally:
            self.selecting = False

    def selection_changed(self, current, previous=None):
        self.select_species(current, previous)
        if current is not None and not self.selecting:
            self.activate_selected()

    def activate_selected(self, item=None):
        if self.loading:
            return
        for entry in self.draft["pets"]:
            if entry["species"] != self.species:
                entry["enabled"] = False
        self.loading = True
        self.enabled.setChecked(True)
        if not any(check.isChecked() for check in self.color_checks.values()):
            color = self.preview_color.currentData()
            self.color_checks[color].setChecked(True)
        self.loading = False
        self.changed()

    def select_species(self, current, previous=None):
        if current is None:
            return
        self.loading = True
        self.species = current.data(QtCore.Qt.ItemDataRole.UserRole)
        entry = self.entry()
        self.title.setText(self.species.capitalize())
        self.enabled.setChecked(entry.get("enabled", True))
        self.draggable.setChecked(entry.get("draggable", False))
        self.physics.setChecked(entry.get("physics_enabled", False))
        self.physics.setToolTip(PETS_DATA[self.species].get("physics", {}).get(
            "description", "Ligada: gravidade, arremesso e quique leve. Desligada: o pet permanece onde você o soltar."))
        while self.colors_layout.count():
            self.colors_layout.takeAt(0).widget().deleteLater()
        self.color_checks = {}
        for index, color in enumerate(PETS_DATA[self.species]["colors"]):
            check = QtWidgets.QCheckBox({"blue": "Azul", "white": "Branco", "brown": "Marrom",
                                        "green": "Verde", "red": "Vermelho"}.get(color, color.capitalize()))
            check.setChecked(color in entry.get("colors", []))
            check.toggled.connect(self.changed)
            self.colors_layout.addWidget(check, index//2, index%2)
            self.color_checks[color] = check
        self.preview_color.clear()
        for color in PETS_DATA[self.species]["colors"]:
            self.preview_color.addItem(self.color_checks[color].text(), color)
        color = self.preview_color.currentData()
        path = next(iter(PETS_DATA[self.species]["states"][color].values()))
        with Image.open(config_io.BASE_DIR / path) as gif:
            original_height = gif.height
        self.size.clear()
        for key, text, height in SIZES:
            self.size.addItem(f"{text} · {height or original_height} px", key)
        self.size.setCurrentIndex(max(0, self.size.findData(entry.get("size", "Original"))))
        self.movement.setValue(round(entry.get("movement_multiplier", 1.0)*100))
        self.animation.setValue(round(entry.get("animation_multiplier", 1.0)*100))
        self.loading = False
        self.color_preview_changed()
        self.update_status()

    def color_preview_changed(self):
        if self.loading:
            return
        previous = self.preview_state.currentData()
        self.preview_state.blockSignals(True)
        self.preview_state.clear()
        for state in PETS_DATA[self.species]["states"][self.preview_color.currentData()]:
            self.preview_state.addItem(STATE_NAMES.get(state, state.replace("_", " ").capitalize()), state)
        self.preview_state.setCurrentIndex(max(0, self.preview_state.findData(previous or "idle")))
        self.preview_state.blockSignals(False)
        self.update_preview()

    def update_preview(self):
        if self.loading or self.preview_state.currentData() is None:
            return
        self.movement_value.setText(f"{self.movement.value()/100:.2f}×".replace(".", ","))
        self.animation_value.setText(f"{self.animation.value()/100:.2f}×".replace(".", ","))
        try:
            self.preview.configure(self.species, self.preview_color.currentData(), self.preview_state.currentData(),
                                   self.size.currentData(), self.entry().get("fps", 8), self.movement.value()/100,
                                   self.animation.value()/100, self.preview_direction.currentData())
            self.preview_info.setText(f"Prévia adaptada · canvas real: {self.preview.frames[0].height()} px\n"
                                      f"Deslocamento: {self.preview.velocity:.1f} px/s".replace(".", ","))
        except (OSError, KeyError, ValueError) as error:
            self.preview.frames = []
            self.preview.update()
            self.preview_info.setText(f"Não foi possível carregar a prévia: {error}")

    def changed(self):
        if self.loading:
            return
        entry = copy.deepcopy(self.entry())
        entry.update(enabled=self.enabled.isChecked(), colors=[c for c, w in self.color_checks.items() if w.isChecked()],
                     size=self.size.currentData(), draggable=self.draggable.isChecked(),
                     physics_enabled=self.physics.isChecked(),
                     movement_multiplier=self.movement.value()/100, animation_multiplier=self.animation.value()/100)
        for index, existing in enumerate(self.draft["pets"]):
            if existing["species"] == self.species:
                self.draft["pets"][index] = entry
                break
        else:
            self.draft["pets"].append(entry)
        self.layer = self.layer_combo.currentData()
        self.update_preview()
        self.update_status()

    def layer_changed(self):
        if not self.loading:
            self.layer = self.layer_combo.currentData()
            self.update_status()

    def is_dirty(self):
        return self.draft != self.original or self.layer != self.config.get("layer", "front")

    def update_status(self):
        dirty = self.is_dirty()
        self.apply_button.setEnabled(dirty)
        self.discard_button.setEnabled(dirty)
        self.status.setText("Alterações ainda não aplicadas" if dirty else "Tudo salvo · quatro cliques na Muuri abrem o painel")

    def discard(self):
        self.draft = copy.deepcopy(self.original)
        self.layer = self.config.get("layer", "front")
        self.loading = True
        self.layer_combo.setCurrentIndex(max(0, self.layer_combo.findData(self.layer)))
        self.loading = False
        self.select_species(self.species_list.currentItem())

    def apply(self):
        if not self.is_dirty():
            return True
        try:
            original_map = {e["species"]: e for e in self.original["pets"]}
            documents = {}
            if self.draft != self.original:
                current = config_io.read_json(config_io.LIST_FILE)
                entries = {e["species"]: e for e in current["pets"]}
                for entry in self.draft["pets"]:
                    if entry == original_map.get(entry["species"]):
                        continue
                    if entry.get("enabled") and not entry.get("colors"):
                        raise ValueError(f"Selecione pelo menos uma cor para {entry['species'].capitalize()}.")
                    target = entries.setdefault(entry["species"], {"species": entry["species"]})
                    target.update({key: copy.deepcopy(entry[key]) for key in FIELDS if key in entry})
                current["pets"] = list(entries.values())
                documents[config_io.LIST_FILE] = current
            if self.layer != self.config.get("layer", "front"):
                current = config_io.read_json(config_io.CONFIG_FILE)
                current["layer"] = self.layer
                documents[config_io.CONFIG_FILE] = current
            before = {path: config_io.read_json(path) for path in documents}
            config_io.write_configs(documents)
            try:
                if not self.owner.start_refresh():
                    raise RuntimeError("Não foi possível atualizar os pets.")
            except Exception:
                config_io.write_configs(before)
                self.owner.start_refresh()
                raise
            self.original = config_io.read_json(config_io.LIST_FILE)
            self.config = config_io.read_json(config_io.CONFIG_FILE)
            self.draft = copy.deepcopy(self.original)
            self.select_species(self.species_list.currentItem())
            self.status.setText("Alterações aplicadas e salvas")
            return True
        except Exception as error:
            self.status.setText(f"Não foi possível aplicar: {error}")
            QtWidgets.QMessageBox.warning(self, "Não foi possível aplicar", str(error))
            return False

    def allow_close(self):
        if not self.is_dirty():
            return True
        box = QtWidgets.QMessageBox(self)
        box.setWindowTitle("Alterações pendentes")
        box.setText("O que você quer fazer com as alterações?")
        apply_button = box.addButton("Aplicar", QtWidgets.QMessageBox.ButtonRole.AcceptRole)
        discard_button = box.addButton("Descartar", QtWidgets.QMessageBox.ButtonRole.DestructiveRole)
        box.addButton("Continuar editando", QtWidgets.QMessageBox.ButtonRole.RejectRole)
        box.exec()
        if box.clickedButton() == apply_button:
            return self.apply()
        if box.clickedButton() == discard_button:
            self.discard()
            return True
        return False
