import copy
import html
import time

from PIL import Image
from PyQt6 import QtCore, QtGui, QtWidgets

from . import config_io
from .pets import PETS_DATA
from .petworker import MAX_PETS
from .version import APP_VERSION


SIZES = [("Very Small", "Bem pequeno", 20), ("Small", "Pequeno", 40),
         ("Original", "Original", None), ("Medium", "Médio", 125),
         ("Big", "Grande", 150), ("Really Big", "Bem grande", 200)]
STATE_NAMES = {"idle": "Parada", "walk": "Andando", "walk_fast": "Trotando",
               "run": "Correndo", "lie": "Descansando", "swipe": "Reação",
               "drag": "Sendo arrastada", "fly": "Voando"}
FIELDS = ("enabled", "colors", "size", "draggable", "physics_enabled", "movement_multiplier", "animation_multiplier", "count")
from .panel_style import STYLE


STATUS_ROLE = int(QtCore.Qt.ItemDataRole.UserRole) + 1
CARD_COLORS = ["#dce6ff", "#e0efd7", "#f9e4d5", "#e6e2fc", "#ece5f7", "#f6e5ef"]


class PetCollection(QtWidgets.QListWidget):
    """Wrapping collection with one scroll area and predictable keyboard navigation."""
    def __init__(self):
        super().__init__()
        self.setViewMode(QtWidgets.QListView.ViewMode.IconMode)
        self.setFlow(QtWidgets.QListView.Flow.LeftToRight)
        self.setWrapping(True)
        self.setMovement(QtWidgets.QListView.Movement.Static)
        self.setResizeMode(QtWidgets.QListView.ResizeMode.Adjust)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setMouseTracking(True)
        self.setMinimumWidth(270)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        width = self.viewport().width()
        columns = 3 if width >= 630 else 2
        self.setGridSize(QtCore.QSize(max(120, (width-8)//columns), 158))


class PetCardDelegate(QtWidgets.QStyledItemDelegate):
    """Use the original pet art, with separate selection and applied activity labels."""
    def sizeHint(self, option, index):
        size = self.parent().gridSize()
        return size if size.isValid() else QtCore.QSize(170, 158)

    def paint(self, painter, option, index):
        painter.save()
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        rect = QtCore.QRectF(option.rect.adjusted(4, 4, -6, -6))
        selected = bool(option.state & QtWidgets.QStyle.StateFlag.State_Selected)
        hovered = bool(option.state & QtWidgets.QStyle.StateFlag.State_MouseOver)
        painter.setBrush(QtGui.QColor("#edf1ff" if selected else "#ffffff"))
        painter.setPen(QtGui.QPen(QtGui.QColor("#4265dd" if selected else "#a6b7ed" if hovered else "#e7eaf3"), 2 if selected else 1))
        painter.drawRoundedRect(rect, 16, 16)
        font = QtGui.QFont("Segoe UI")
        font.setPixelSize(11)
        painter.setFont(font)
        painter.setPen(QtGui.QColor("#66718b"))
        painter.drawText(rect.adjusted(12, 9, -12, -9), QtCore.Qt.AlignmentFlag.AlignTop |
                         QtCore.Qt.AlignmentFlag.AlignLeft, f"{index.row()+1:02d}")
        glow = QtGui.QRadialGradient(rect.center().x(), rect.top()+62, rect.width()/2)
        glow.setColorAt(0, QtGui.QColor(CARD_COLORS[index.row() % len(CARD_COLORS)]))
        edge = QtGui.QColor(CARD_COLORS[index.row() % len(CARD_COLORS)])
        edge.setAlpha(0)
        glow.setColorAt(1, edge)
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.setBrush(glow)
        painter.drawEllipse(rect.adjusted(10, 18, -10, -45))
        icon = index.data(QtCore.Qt.ItemDataRole.DecorationRole)
        if icon:
            icon.paint(painter, QtCore.QRect(int(rect.center().x())-42, int(rect.top())+24, 84, 77))
        font.setPixelSize(14)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QtGui.QColor("#233253"))
        painter.drawText(rect.adjusted(12, 0, -12, -27), QtCore.Qt.AlignmentFlag.AlignBottom |
                         QtCore.Qt.AlignmentFlag.AlignLeft, index.data())
        font.setPixelSize(11)
        font.setBold(False)
        painter.setFont(font)
        painter.setPen(QtGui.QColor("#66718b"))
        status = index.data(STATUS_ROLE) or ""
        text = QtGui.QFontMetrics(font).elidedText(status, QtCore.Qt.TextElideMode.ElideRight, int(rect.width())-24)
        painter.drawText(rect.adjusted(12, 0, -12, -10), QtCore.Qt.AlignmentFlag.AlignBottom |
                         QtCore.Qt.AlignmentFlag.AlignLeft, text)
        if option.state & QtWidgets.QStyle.StateFlag.State_HasFocus:
            painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
            painter.setPen(QtGui.QPen(QtGui.QColor("#4265dd"), 1, QtCore.Qt.PenStyle.DotLine))
            painter.drawRoundedRect(rect.adjusted(4, 4, -4, -4), 12, 12)
        painter.restore()



def pet_icon(species):
    data = PETS_DATA[species]
    color = data["colors"][0]
    states = data["states"][color]
    path = states.get("idle", next(iter(states.values())))
    try:
        with Image.open(config_io.BASE_DIR / path) as gif:
            frame = gif.convert("RGBA")
            frame = frame.crop(frame.getchannel("A").getbbox())
            raw = frame.tobytes()
            image = QtGui.QImage(raw, frame.width, frame.height, frame.width * 4,
                                 QtGui.QImage.Format.Format_RGBA8888).copy()
        return QtGui.QIcon(QtGui.QPixmap.fromImage(image))
    except (OSError, ValueError):
        return QtGui.QIcon()


def label(text, name=None, wrap=False):
    widget = QtWidgets.QLabel(text)
    if name:
        widget.setObjectName(name)
    widget.setWordWrap(wrap)
    return widget


class DetailTabs(QtWidgets.QTabWidget):
    """Size the inspector for its visible page, rather than its longest page."""
    def __init__(self):
        super().__init__()
        self.currentChanged.connect(self.updateGeometry)

    def minimumSizeHint(self):
        page = self.currentWidget()
        size = page.minimumSizeHint() if page else QtCore.QSize()
        return QtCore.QSize(max(size.width(), self.tabBar().sizeHint().width()),
                            size.height() + self.tabBar().sizeHint().height() + 4)

    def sizeHint(self):
        return self.minimumSizeHint()


class Preview(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(270, 210)
        self.frames = []
        self.cache = {}
        self.frame_index = 0
        self.offset = 0
        self.last_tick = time.monotonic()
        self.paused = False
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
        if self.frames and not self.paused:
            self.frame_index = (self.frame_index + elapsed * self.fps) % len(self.frames)
            scale = self.display_scale()
            span = max(1, self.width() - self.frames[0].width() * scale - 24)
            self.offset = (self.offset + elapsed * self.velocity * scale) % span
            self.update()

    def display_scale(self):
        return min(3, (self.width()-24)/self.frames[0].width(),
                   (self.height()-24)/self.frames[0].height())

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setClipRect(self.rect())
        for y in range(0, self.height(), 16):
            for x in range(0, self.width(), 16):
                painter.fillRect(x, y, 16, 16, QtGui.QColor("#e8ecf9" if (x//16+y//16)%2 else "#f1f3fd"))
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
        outer = QtWidgets.QBoxLayout(QtWidgets.QBoxLayout.Direction.LeftToRight, self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        self.shell_layout = outer
        self.sidebar = QtWidgets.QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar_layout = QtWidgets.QBoxLayout(QtWidgets.QBoxLayout.Direction.TopToBottom, self.sidebar)
        self.sidebar_layout.setContentsMargins(14, 20, 14, 20)
        self.sidebar_layout.setSpacing(16)
        brand = QtWidgets.QWidget()
        brand_row = QtWidgets.QHBoxLayout(brand)
        brand_row.setContentsMargins(0, 0, 0, 0)
        logo = label("")
        logo.setPixmap(pet_icon("muuri").pixmap(32, 36))
        brand_row.addWidget(logo)
        brand_row.addWidget(label("muuri.", "brand"))
        self.sidebar_layout.addWidget(brand)
        self.nav_caption = label("SEU ESPAÇO", "eyebrow")
        self.sidebar_layout.addWidget(self.nav_caption)
        self.nav_widget = QtWidgets.QWidget()
        self.nav_layout = QtWidgets.QBoxLayout(QtWidgets.QBoxLayout.Direction.TopToBottom, self.nav_widget)
        self.nav_layout.setContentsMargins(0, 0, 0, 0)
        self.nav_layout.setSpacing(6)
        self.nav_group = QtWidgets.QButtonGroup(self)
        for index, text in enumerate(("Pets", "Preferências", "Sobre o Muuri")):
            button = QtWidgets.QPushButton(text)
            button.setObjectName("navigation")
            button.setCheckable(True)
            button.setMinimumWidth(58)
            self.nav_group.addButton(button, index)
            self.nav_layout.addWidget(button)
        self.nav_group.button(0).setChecked(True)
        self.sidebar_layout.addWidget(self.nav_widget)
        self.sidebar_layout.addStretch(1)
        self.sidebar_note = label("Um pouco de companhia.\nDo seu jeito.", "muted", True)
        self.sidebar_layout.addWidget(self.sidebar_note)
        outer.addWidget(self.sidebar)

        body = QtWidgets.QWidget()
        body.setObjectName("body")
        body_layout = QtWidgets.QVBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)
        header = QtWidgets.QHBoxLayout()
        header.setContentsMargins(24, 22, 24, 18)
        heading = QtWidgets.QVBoxLayout()
        heading.setSpacing(5)
        self.header_caption = label("PEQUENAS COMPANHIAS, GRANDES DIAS", "eyebrow")
        heading.addWidget(self.header_caption)
        heading.addWidget(label("Seu pequeno universo.", "pageTitle"))
        header.addLayout(heading, 1)
        self.total_label = label("", "muted")
        header.addWidget(self.total_label)
        body_layout.addLayout(header)
        self.tabs = QtWidgets.QTabWidget()
        self.tabs.tabBar().hide()
        body_layout.addWidget(self.tabs, 1)
        self.nav_group.idClicked.connect(self.tabs.setCurrentIndex)
        self.tabs.currentChanged.connect(lambda index: self.nav_group.button(index).setChecked(True))
        outer.addWidget(body, 1)

        pets_page = QtWidgets.QWidget()
        pets_page.setObjectName("petsContent")
        main_row = QtWidgets.QHBoxLayout(pets_page)
        main_row.setContentsMargins(22, 0, 22, 18)
        main_row.setSpacing(20)
        collection = QtWidgets.QVBoxLayout()
        collection.setSpacing(12)
        views = QtWidgets.QHBoxLayout()
        self.view_group = QtWidgets.QButtonGroup(self)
        for index, text in enumerate(("Coleção", "Na tela")):
            button = QtWidgets.QPushButton(text)
            button.setObjectName("view")
            button.setCheckable(True)
            self.view_group.addButton(button, index)
            views.addWidget(button)
        self.view_group.button(0).setChecked(True)
        self.view_group.idClicked.connect(self.filter_collection)
        views.addStretch()
        collection.addLayout(views)
        self.search = QtWidgets.QLineEdit()
        self.search.setObjectName("search")
        self.search.setPlaceholderText("Encontre seu companheiro")
        self.search.setAccessibleName("Buscar pet pelo nome")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self.filter_collection)
        collection.addWidget(self.search)
        self.species_list = PetCollection()
        self.species_list.setObjectName("collection")
        self.species_list.setAccessibleName("Coleção de pets; selecione para ver os ajustes")
        self.species_list.setItemDelegate(PetCardDelegate(self.species_list))
        featured = ("muuri", "fefo", "cato", "manu", "eco")
        for species in sorted(PETS_DATA, key=lambda name: (featured.index(name) if name in featured else len(featured), name)):
            item = QtWidgets.QListWidgetItem(pet_icon(species), species.capitalize())
            item.setData(QtCore.Qt.ItemDataRole.UserRole, species)
            self.species_list.addItem(item)
        collection.addWidget(self.species_list, 1)
        self.empty_box = QtWidgets.QWidget()
        empty_layout = QtWidgets.QVBoxLayout(self.empty_box)
        empty_layout.addStretch()
        self.empty_label = label("", "sectionTitle", True)
        self.empty_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(self.empty_label)
        self.explore_button = QtWidgets.QPushButton("Explorar coleção")
        self.explore_button.clicked.connect(self.explore_collection)
        empty_layout.addWidget(self.explore_button, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        empty_layout.addStretch()
        collection.addWidget(self.empty_box, 1)
        self.empty_box.hide()
        collection_footer = QtWidgets.QHBoxLayout()
        self.collection_info = label("", "muted")
        collection_footer.addWidget(self.collection_info, 1)
        self.remove_all_button = QtWidgets.QPushButton("Remover todos")
        self.remove_all_button.setObjectName("removeAll")
        self.remove_all_button.setToolTip("Prepara a remoção de todos os pets. Confirme em Aplicar alterações.")
        collection_footer.addWidget(self.remove_all_button)
        collection.addLayout(collection_footer)
        main_row.addLayout(collection, 1)

        self.detail_scroll = QtWidgets.QScrollArea()
        self.detail_scroll.setWidgetResizable(True)
        self.detail_scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.detail_scroll.setMinimumWidth(0)
        controls = QtWidgets.QFrame()
        controls.setObjectName("detailsBody")
        form = QtWidgets.QVBoxLayout(controls)
        form.setContentsMargins(18, 16, 18, 14)
        form.setSpacing(10)
        detail_heading = QtWidgets.QHBoxLayout()
        detail_copy = QtWidgets.QVBoxLayout()
        detail_copy.setSpacing(4)
        detail_copy.addWidget(label("SEU COMPANHEIRO", "eyebrow"))
        self.title = label("", "title")
        detail_copy.addWidget(self.title)
        detail_heading.addLayout(detail_copy, 1)
        self.pet_badge = label("", "badge")
        detail_heading.addWidget(self.pet_badge, alignment=QtCore.Qt.AlignmentFlag.AlignVCenter)
        form.addLayout(detail_heading)
        preview_card = QtWidgets.QFrame()
        preview_card.setObjectName("hero")
        preview_layout = QtWidgets.QVBoxLayout(preview_card)
        preview_layout.setContentsMargins(10, 8, 10, 8)
        preview_layout.setSpacing(4)
        preview_heading = QtWidgets.QHBoxLayout()
        preview_heading.addWidget(label("Prévia animada", "muted"), 1)
        self.pause_button = QtWidgets.QPushButton("Pausar")
        self.pause_button.setObjectName("previewAction")
        self.pause_button.setAccessibleName("Pausar ou reproduzir a prévia")
        preview_heading.addWidget(self.pause_button)
        preview_layout.addLayout(preview_heading)
        self.preview = Preview()
        self.preview.setMinimumSize(120, 130)
        self.preview.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        self.preview.setFixedHeight(130)
        self.preview.setAccessibleName("Prévia animada do pet, com fundo de transparência")
        preview_layout.addWidget(self.preview)
        self.preview_color = QtWidgets.QComboBox()
        self.preview_state = QtWidgets.QComboBox()
        self.preview_direction = QtWidgets.QComboBox()
        self.preview_direction.addItem("Para a direita", 1)
        self.preview_direction.addItem("Para a esquerda", -1)
        self.preview_color.setAccessibleName("Cor da prévia")
        self.preview_state.setAccessibleName("Animação da prévia")
        self.preview_direction.setAccessibleName("Direção da prévia")
        preview_options = QtWidgets.QHBoxLayout()
        preview_options.addWidget(self.preview_state, 1)
        self.flip_button = QtWidgets.QPushButton("Espelhar")
        self.flip_button.setObjectName("previewAction")
        self.flip_button.setAccessibleName("Espelhar direção da prévia")
        self.flip_button.clicked.connect(lambda: self.preview_direction.setCurrentIndex(1-self.preview_direction.currentIndex()))
        preview_options.addWidget(self.flip_button)
        self.preview_direction.hide()
        preview_layout.addLayout(preview_options)
        self.preview_card = preview_card
        self.preview_toggle = QtWidgets.QPushButton("Mostrar prévia")
        self.preview_toggle.setObjectName("previewAction")
        self.preview_toggle.setCheckable(True)
        self.preview_toggle.setChecked(True)
        self.preview_toggle.toggled.connect(self.set_preview_visible)
        self.preview_toggle.hide()
        form.addWidget(self.preview_toggle)
        form.addWidget(preview_card)
        self.enabled = QtWidgets.QCheckBox("Mostrar na área de trabalho")
        form.addWidget(self.enabled)
        quantity_row = QtWidgets.QHBoxLayout()
        quantity_copy = QtWidgets.QVBoxLayout()
        quantity_copy.setSpacing(3)
        quantity_copy.addWidget(label("Quantidade por cor"))
        self.quantity_note = label("", "muted", True)
        quantity_copy.addWidget(self.quantity_note)
        quantity_row.addLayout(quantity_copy, 1)
        self.remove_one_button = QtWidgets.QPushButton("−")
        self.remove_one_button.setObjectName("step")
        self.remove_one_button.setFixedWidth(28)
        self.remove_one_button.setAccessibleName("Remover uma unidade de cada cor marcada")
        self.remove_one_button.setToolTip("Remover 1 por cor · confirme em Aplicar")
        quantity_row.addWidget(self.remove_one_button)
        self.quantity = QtWidgets.QLineEdit("1")
        self.quantity.setObjectName("quantity")
        self.quantity.setAccessibleName("Quantidade de pets por cor")
        self.quantity.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.quantity.setValidator(QtGui.QIntValidator(0, MAX_PETS, self.quantity))
        self.quantity.setFixedWidth(48)
        self.quantity.setToolTip(f"Máximo de {MAX_PETS} pets no total, contando todas as cores e espécies. Zero remove ao aplicar.")
        quantity_row.addWidget(self.quantity)
        self.add_one_button = QtWidgets.QPushButton("+")
        self.add_one_button.setObjectName("step")
        self.add_one_button.setFixedWidth(28)
        self.add_one_button.setAccessibleName("Adicionar uma unidade de cada cor marcada")
        quantity_row.addWidget(self.add_one_button)
        form.addLayout(quantity_row)
        self.settings_tabs = DetailTabs()
        appearance = QtWidgets.QWidget()
        appearance_form = QtWidgets.QVBoxLayout(appearance)
        appearance_form.setContentsMargins(0, 10, 0, 0)
        appearance_form.addWidget(label("Tamanho"))
        self.size = QtWidgets.QComboBox()
        self.size.setAccessibleName("Tamanho do pet")
        appearance_form.addWidget(self.size)
        appearance_form.addWidget(label("Cores ativas"))
        self.colors_box = QtWidgets.QWidget()
        self.colors_layout = QtWidgets.QGridLayout(self.colors_box)
        self.colors_layout.setContentsMargins(0, 0, 0, 0)
        appearance_form.addWidget(self.colors_box)
        self.preview_color_label = label("Cor da prévia")
        appearance_form.addWidget(self.preview_color_label)
        appearance_form.addWidget(self.preview_color)
        appearance_form.addStretch()
        behavior = QtWidgets.QWidget()
        behavior_form = QtWidgets.QVBoxLayout(behavior)
        behavior_form.setContentsMargins(0, 10, 0, 0)
        behavior_form.setSpacing(6)
        self.draggable = QtWidgets.QCheckBox("Arrastar com o mouse")
        behavior_form.addWidget(self.draggable)
        self.physics = QtWidgets.QCheckBox("Ativar física")
        behavior_form.addWidget(self.physics)
        self.physics_note = label("", "muted", True)
        behavior_form.addWidget(self.physics_note)
        self.movement, self.movement_value = self.add_speed(behavior_form, "Movimento")
        self.animation, self.animation_value = self.add_speed(behavior_form, "Animação")
        self.reset_speed_button = QtWidgets.QPushButton("Restaurar velocidades para 1×")
        self.reset_speed_button.setObjectName("textAction")
        self.reset_speed_button.clicked.connect(self.reset_speeds)
        behavior_form.addWidget(self.reset_speed_button)
        behavior_form.addStretch()
        self.settings_tabs.addTab(appearance, "Aparência")
        self.settings_tabs.addTab(behavior, "Comportamento")
        form.addWidget(self.settings_tabs)
        self.preview_info = label("", "muted", True)
        self.add_button = QtWidgets.QPushButton("Adicionar à tela")
        self.add_button.setObjectName("add")
        self.remove_species_button = QtWidgets.QPushButton("Remover espécie")
        self.remove_species_button.setObjectName("textAction")
        form.addStretch()
        self.detail_scroll.setWidget(controls)
        self.detail_card = QtWidgets.QFrame()
        self.detail_card.setObjectName("card")
        self.detail_card.setFixedWidth(340)
        detail_layout = QtWidgets.QVBoxLayout(self.detail_card)
        detail_layout.setContentsMargins(1, 1, 1, 10)
        detail_layout.setSpacing(0)
        detail_layout.addWidget(self.detail_scroll, 1)
        detail_actions = QtWidgets.QVBoxLayout()
        detail_actions.setContentsMargins(18, 8, 18, 0)
        detail_actions.setSpacing(4)
        detail_actions.addWidget(self.preview_info)
        detail_actions.addWidget(self.add_button)
        detail_actions.addWidget(self.remove_species_button)
        detail_layout.addLayout(detail_actions)
        main_row.addWidget(self.detail_card)
        self.pets_scroll = self.detail_scroll
        self.tabs.addTab(pets_page, "Pets")
        self.build_preferences()
        self.build_credits()

        footer = QtWidgets.QFrame()
        footer.setObjectName("footer")
        footer_row = QtWidgets.QHBoxLayout(footer)
        footer_row.setContentsMargins(22, 12, 22, 12)
        status_copy = QtWidgets.QVBoxLayout()
        status_copy.setSpacing(3)
        self.status = label("", "statusTitle")
        self.status_detail = label("", "statusDetail", True)
        self.status_detail.setAccessibleName("Resumo das alterações pendentes")
        status_copy.addWidget(self.status)
        status_copy.addWidget(self.status_detail)
        footer_row.addLayout(status_copy, 1)
        self.discard_button = QtWidgets.QPushButton("Descartar")
        self.apply_button = QtWidgets.QPushButton("Aplicar alterações")
        self.apply_button.setObjectName("primary")
        footer_row.addWidget(self.discard_button)
        footer_row.addWidget(self.apply_button)
        body_layout.addWidget(footer)

        for widget in (self.enabled, self.draggable, self.physics):
            widget.toggled.connect(self.changed)
        self.quantity.textChanged.connect(self.changed)
        self.size.currentIndexChanged.connect(self.changed)
        self.movement.valueChanged.connect(self.changed)
        self.animation.valueChanged.connect(self.changed)
        self.layer_combo.currentIndexChanged.connect(self.layer_changed)
        self.preview_color.currentIndexChanged.connect(self.color_preview_changed)
        self.preview_state.currentIndexChanged.connect(self.update_preview)
        self.preview_direction.currentIndexChanged.connect(self.update_preview)
        self.species_list.currentItemChanged.connect(self.selection_changed)
        self.discard_button.clicked.connect(self.discard)
        self.apply_button.clicked.connect(self.apply)
        self.remove_one_button.clicked.connect(self.remove_one)
        self.add_one_button.clicked.connect(self.add_one)
        self.add_button.clicked.connect(self.add_one)
        self.remove_species_button.clicked.connect(lambda: self.quantity.setText("0"))
        self.remove_all_button.clicked.connect(self.remove_all)
        self.pause_button.clicked.connect(self.toggle_preview)
        self.loading = False
        self.select("muuri")

    def build_preferences(self):
        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(page)
        layout.setContentsMargins(26, 12, 26, 26)
        layout.setSpacing(18)
        layout.addWidget(label("DO SEU JEITO", "eyebrow"))
        layout.addWidget(label("Preferências", "title"))
        layout.addWidget(label("Um espaço confortável para você e seus pets.", "muted"))
        layout.addSpacing(12)
        layout.addWidget(label("Camada de exibição", "sectionTitle"))
        layout.addWidget(label("Escolha onde seus companheiros ficam em relação às outras janelas.", "muted", True))
        self.layer_combo = QtWidgets.QComboBox()
        self.layer_combo.setAccessibleName("Camada de exibição dos pets")
        self.layer_combo.addItem("À frente das janelas", "front")
        self.layer_combo.addItem("Atrás das janelas", "back")
        self.layer_combo.setCurrentIndex(max(0, self.layer_combo.findData(self.layer)))
        self.layer_combo.setMaximumWidth(320)
        layout.addWidget(self.layer_combo)
        layout.addSpacing(16)
        layout.addWidget(label("Sempre por perto", "sectionTitle"))
        layout.addWidget(label("Abra os ajustes pelo ícone da bandeja ou com quatro cliques rápidos nos pets que têm esse gesto habilitado. São quatro cliques em até 1,5 segundo, sem arrastar; funciona mesmo com o arraste desligado.", "muted", True))
        layout.addWidget(label("Fechar este painel mantém os pets ativos. Para encerrar o aplicativo, use Sair no menu da bandeja.", "muted", True))
        layout.addSpacing(16)
        layout.addWidget(label("Atualizações", "sectionTitle"))
        layout.addWidget(label(f"Muuri {APP_VERSION}", "muted"))
        self.update_status_label = label("A versão instalada no Windows procura atualizações ao abrir. No macOS, consulte os downloads do projeto.", "muted", True)
        layout.addWidget(self.update_status_label)
        self.update_button = QtWidgets.QPushButton("Verificar atualizações")
        self.update_button.setMaximumWidth(300)
        layout.addWidget(self.update_button)
        layout.addStretch()
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(page)
        self.tabs.addTab(scroll, "Preferências")

    def build_credits(self):
        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(page)
        layout.setContentsMargins(26, 12, 26, 20)
        layout.addWidget(label("UM COMPANHEIRO. DO SEU JEITO.", "eyebrow"))
        layout.addWidget(label("Feito para fazer companhia.", "title"))
        credits = QtWidgets.QTextBrowser()
        credits.setAccessibleName("Créditos do Muuri e licença integral do DeskPets")
        credits.setOpenExternalLinks(True)
        license_path = config_io.BASE_DIR.parent / "LICENSE"
        license_text = license_path.read_text(encoding="utf-8") if license_path.exists() else "Consulte LICENSE na distribuição original."
        credits.setHtml(f'<h2>Muuri {APP_VERSION}</h2><h3>Créditos e código aberto</h3><p>DeskPets por Minniti Julien (Jumitti).</p>'
                        '<p><a href="https://github.com/Jumitti/DeskPets">Projeto original</a> · '
                        '<a href="https://github.com/Jumitti/DeskPets#credits">Créditos originais</a></p>'
                        '<p>Inspirado em <a href="https://github.com/tonybaloney/vscode-pets">vscode-pets</a>, '
                        'por tonybaloney. As mídias originais vêm desse projeto e seus créditos continuam aplicáveis.</p>'
                        '<h3>Companheiros</h3>'
                        '<p>Muuri: design de referência fornecido pelo usuário; animações adaptadas para DeskPets.</p>'
                        '<p>Manu: design de referência fornecido pelo usuário; animações adaptadas para DeskPets com geração de imagens.</p>'
                        '<p>Eco: referência visual fornecida pelo usuário; base preparada com geração de imagens e animações feitas a partir da mesma base.</p>'
                        '<p>Fefo: personagem integrado a partir da referência canônica fefo.svg fornecida pelo usuário.</p>'
                        '<p>Cato: personagem integrado a partir dos materiais de referência fornecidos pelo usuário.</p>'
                        '<h3>Licença MIT do DeskPets</h3><pre style="white-space: pre-wrap">'
                        + html.escape(license_text) + '</pre>')
        self.credits_browser = credits
        layout.addWidget(credits, 1)
        self.tabs.addTab(page, "Sobre o Muuri")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not hasattr(self, "preview"):
            return
        compact = self.width() < 1000
        direction = QtWidgets.QBoxLayout.Direction
        self.shell_layout.setDirection(direction.TopToBottom if compact else direction.LeftToRight)
        self.sidebar_layout.setDirection(direction.LeftToRight if compact else direction.TopToBottom)
        self.nav_layout.setDirection(direction.LeftToRight if compact else direction.TopToBottom)
        if compact:
            self.sidebar.setMinimumWidth(0)
            self.sidebar.setMaximumWidth(16777215)
            self.sidebar.setFixedHeight(62)
        else:
            self.sidebar.setFixedWidth(158)
            self.sidebar.setMinimumHeight(0)
            self.sidebar.setMaximumHeight(16777215)
        self.sidebar_layout.setContentsMargins(16, 8 if compact else 20, 16, 8 if compact else 20)
        self.nav_caption.setVisible(not compact)
        self.sidebar_note.setVisible(not compact)
        self.header_caption.setVisible(self.height() >= 660)
        self.preview.setFixedHeight(100 if self.height() < 700 else 130)
        short = self.height() < 700
        self.preview_toggle.setVisible(short)
        if short != getattr(self, "short_layout", False):
            self.preview_toggle.setChecked(not short)
        self.short_layout = short

    def set_preview_visible(self, visible):
        self.preview_card.setVisible(visible)
        self.preview_toggle.setText("Ocultar prévia" if visible else "Mostrar prévia")

    def toggle_preview(self):
        self.preview.paused = not self.preview.paused
        self.pause_button.setText("Reproduzir" if self.preview.paused else "Pausar")

    def reset_speeds(self):
        self.movement.setValue(100)
        self.animation.setValue(100)

    def add_one(self):
        if sum(self.active_count(e) for e in self.draft['pets']) >= MAX_PETS:
            self.show_limit_notice()
            return
        if not self.enabled.isChecked():
            self.activate_selected()
        elif self.quantity.hasAcceptableInput():
            self.quantity.setText(str(int(self.quantity.text()) + 1))

    @staticmethod
    def active_count(entry):
        if not entry or not entry.get("enabled", True):
            return 0
        return entry.get("count", 1) * len(entry.get("colors", []))

    @classmethod
    def visible_counts(cls, entries):
        remaining, counts = MAX_PETS, {}
        for entry in entries:
            count = min(cls.active_count(entry), remaining)
            counts[entry['species']] = counts.get(entry['species'], 0) + count
            remaining -= count
        return counts

    def show_limit_notice(self):
        self.status.setText(f"Limite de {MAX_PETS} pets no total")
        self.status_detail.setText("Remova um pet ou diminua a quantidade antes de adicionar outro.")

    def explore_collection(self):
        self.view_group.button(0).setChecked(True)
        self.search.clear()
        self.filter_collection()

    def filter_collection(self, *_):
        if self.loading:
            return
        visible_counts = self.visible_counts(self.original['pets'])
        draft = {entry['species']: entry for entry in self.draft['pets']}
        query = self.search.text().strip().casefold()
        active_only = self.view_group.checkedId() == 1
        visible = 0
        for row in range(self.species_list.count()):
            item = self.species_list.item(row)
            species = item.data(QtCore.Qt.ItemDataRole.UserRole)
            before, after = visible_counts.get(species, 0), self.active_count(draft.get(species))
            if before != after:
                text = "Será removido" if after == 0 else f"{before} → {after} após aplicar"
            else:
                text = f"{before} na tela" if before else "Pronto para conhecer"
            item.setData(STATUS_ROLE, text)
            item.setToolTip(f"{species.capitalize()} · {text}\nSelecionar abre os ajustes; use Adicionar à tela para ativar.")
            item.setData(QtCore.Qt.ItemDataRole.AccessibleDescriptionRole, text)
            hidden = query not in species.casefold() or (active_only and not (before or after))
            item.setHidden(hidden)
            visible += not hidden
        self.species_list.setVisible(bool(visible))
        self.empty_box.setVisible(not visible)
        self.empty_label.setText("Nenhum companheiro encontrado" if query else "Um espaço para novas companhias")
        self.collection_info.setText(f"{visible} {'espécies nesta seleção' if active_only else 'companheiros para conhecer'}")
        self.view_group.button(0).setText(f"Coleção · {len(PETS_DATA)}")
        self.view_group.button(1).setText(f"Na tela · {sum(count > 0 for count in visible_counts.values())}")
        self.species_list.viewport().update()

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
        data = PETS_DATA[self.species]
        interactive = 'drag' in data['states'][data['colors'][0]]
        return next((e for e in self.draft["pets"] if e["species"] == self.species),
                    {"species": self.species, "colors": [], "enabled": False, "size": "Original",
                     "draggable": interactive, "settings_clicks": 4 if interactive else 0})

    def select(self, species):
        # Opening the panel or selecting a pet programmatically must not enable it.
        self.selecting = True
        try:
            # A tray/gesture request must reveal its pet even through an active filter.
            self.view_group.button(0).setChecked(True)
            self.search.clear()
            self.filter_collection()
            for index in range(self.species_list.count()):
                if self.species_list.item(index).data(QtCore.Qt.ItemDataRole.UserRole) == species:
                    self.species_list.setCurrentRow(index)
                    self.species_list.scrollToItem(self.species_list.item(index))
                    break
        finally:
            self.selecting = False

    def selection_changed(self, current, previous=None):
        self.select_species(current, previous)

    def activate_selected(self, item=None):
        if self.loading or not self.quantity.hasAcceptableInput():
            return
        self.loading = True
        if self.quantity.text() == "0":
            self.quantity.setText("1")
        self.enabled.setChecked(True)
        if not any(check.isChecked() for check in self.color_checks.values()):
            color = self.preview_color.currentData()
            self.color_checks[color].setChecked(True)
        self.loading = False
        self.changed()

    def remove_one(self):
        if self.quantity.hasAcceptableInput():
            self.quantity.setText(str(max(0, int(self.quantity.text())-1)))

    def remove_all(self):
        for entry in self.draft['pets']:
            entry['enabled'] = False
        self.select_species(self.species_list.currentItem())

    def select_species(self, current, previous=None):
        if current is None:
            return
        self.loading = True
        previous_species = getattr(self, "species", None)
        self.species = current.data(QtCore.Qt.ItemDataRole.UserRole)
        entry = self.entry()
        self.title.setText(self.species.capitalize())
        self.enabled.setChecked(entry.get("enabled", True))
        self.quantity.setText(str(entry.get("count", 1)))
        self.draggable.setChecked(entry.get("draggable", False))
        self.physics.setChecked(entry.get("physics_enabled", False))
        self.physics.setToolTip(PETS_DATA[self.species].get("physics", {}).get(
            "description", "Ligada: gravidade, arremesso e quique leve. Desligada: o pet permanece onde você o soltar."))
        self.physics_note.setText(self.physics.toolTip())
        while self.colors_layout.count():
            check = self.colors_layout.takeAt(0).widget()
            check.hide()
            check.deleteLater()
        self.color_checks = {}
        for index, color in enumerate(PETS_DATA[self.species]["colors"]):
            check = QtWidgets.QCheckBox({"blue": "Azul", "white": "Branco", "brown": "Marrom",
                                        "green": "Verde", "red": "Vermelho", "orange": "Laranja",
                                        "gray": "Cinza", "black": "Preto", "yellow": "Amarelo"}.get(color, color.capitalize()))
            check.setChecked(color in entry.get("colors", []))
            check.toggled.connect(self.changed)
            self.colors_layout.addWidget(check, index//2, index%2)
            self.color_checks[color] = check
        self.preview_color.clear()
        for color in PETS_DATA[self.species]["colors"]:
            self.preview_color.addItem(self.color_checks[color].text(), color)
        multiple_colors = self.preview_color.count() > 1
        self.preview_color.setVisible(multiple_colors)
        self.preview_color_label.setVisible(multiple_colors)
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
        if previous_species != self.species:
            self.detail_scroll.verticalScrollBar().setValue(0)

    def color_preview_changed(self):
        if self.loading:
            return
        previous = self.preview_state.currentData()
        self.preview_state.blockSignals(True)
        self.preview_state.clear()
        for state in PETS_DATA[self.species]["states"][self.preview_color.currentData()]:
            self.preview_state.addItem(STATE_NAMES.get(state, state.replace("_", " ").capitalize()), state)
        self.pet_badge.setText(self.preview_color.currentText())
        self.pet_badge.setToolTip(f"{self.preview_state.count()} animações disponíveis")
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
            self.preview_info.setText("Explore a prévia. Seu desktop só muda ao aplicar.")
            self.preview_info.setToolTip(f"Canvas: {self.preview.frames[0].height()} px · movimento: {self.preview.velocity:.1f} px/s".replace(".", ","))
            self.flip_button.setToolTip(self.preview_direction.currentText())
        except (OSError, KeyError, ValueError) as error:
            self.preview.frames = []
            self.preview.update()
            self.preview_info.setText(f"Não foi possível carregar a prévia: {error}")

    def changed(self):
        if self.loading:
            return
        entry = copy.deepcopy(self.entry())
        if self.quantity.hasAcceptableInput():
            count = int(self.quantity.text())
            self.loading = True
            if self.sender() is self.enabled and self.enabled.isChecked() and count == 0:
                count = 1
                self.quantity.setText("1")
            elif count == 0:
                self.enabled.setChecked(False)
            elif self.sender() is self.quantity and entry.get('count', 1) == 0:
                self.enabled.setChecked(True)
            self.loading = False
            entry["count"] = count
        entry.update(enabled=self.enabled.isChecked(), colors=[c for c, w in self.color_checks.items() if w.isChecked()],
                     size=self.size.currentData(), draggable=self.draggable.isChecked(),
                     physics_enabled=self.physics.isChecked(),
                     movement_multiplier=self.movement.value()/100, animation_multiplier=self.animation.value()/100)
        before = sum(self.active_count(e) for e in self.draft['pets'])
        after = sum(self.active_count(e) for e in self.draft['pets'] if e['species'] != self.species) + self.active_count(entry)
        if after > MAX_PETS and after > before:
            self.select_species(self.species_list.currentItem())
            self.show_limit_notice()
            return
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
        total = sum(self.active_count(e) for e in self.draft['pets'])
        valid_quantity = self.quantity.hasAcceptableInput()
        active = self.enabled.isChecked() and self.quantity.hasAcceptableInput() and int(self.quantity.text()) > 0
        self.remove_one_button.setEnabled(active)
        self.remove_species_button.setEnabled(self.active_count(self.entry()) > 0)
        self.remove_all_button.setEnabled(any(entry.get('enabled', True) for entry in self.draft['pets']))
        self.apply_button.setEnabled(dirty and valid_quantity and total <= MAX_PETS)
        self.discard_button.setEnabled(dirty)
        colors = max(1, sum(check.isChecked() for check in self.color_checks.values()))
        extra = colors if active else colors * max(1, int(self.quantity.text()) if valid_quantity else 1)
        can_add = valid_quantity and total + extra <= MAX_PETS
        self.add_one_button.setEnabled(can_add)
        self.add_button.setEnabled(can_add)
        for button in (self.add_one_button, self.add_button):
            button.setToolTip("Adicionar pet" if can_add else f"Limite de {MAX_PETS} pets no total; reduza a quantidade para adicionar.")
        original = {e['species']: e for e in self.original['pets']}
        summaries = []
        for entry in self.draft['pets']:
            old = original.get(entry['species'])
            if entry != old:
                before, after = self.active_count(old), self.active_count(entry)
                summaries.append(f"{entry['species'].capitalize()}: {before} → {after}" if before != after else
                                 f"Ajustes de {entry['species'].capitalize()}")
        if self.layer != self.config.get('layer', 'front'):
            summaries.append("Camada de exibição")
        self.status.setText(f"{len(summaries)} {'alteração pendente' if len(summaries) == 1 else 'alterações pendentes'}" if dirty else "Tudo do seu jeito")
        full_summary = " · ".join(summaries)
        self.status_detail.setText(" · ".join(summaries[:2]) + (f" · +{len(summaries)-2}" if len(summaries) > 2 else "") if dirty else "Nenhuma alteração pendente")
        self.status_detail.setToolTip(full_summary)
        visible_counts = self.visible_counts(self.original['pets'])
        self.total_label.setText(f"{sum(visible_counts.values())}/{MAX_PETS} pets na tela")
        before = visible_counts.get(self.species, 0)
        after = self.active_count(self.entry())
        self.quantity_note.setText(f"Na tela: {before} → Após aplicar: {after}" if before != after else
                                   f"{before} na tela" if after else "Desativado · ative para mostrar")
        self.quantity_note.setText(self.quantity_note.text() + f" · Total após aplicar: {total}/{MAX_PETS}")
        if total > MAX_PETS:
            self.show_limit_notice()
        elif not valid_quantity:
            self.status.setText(f"Informe uma quantidade inteira de 0 a {MAX_PETS}.")
        self.filter_collection()

    def discard(self):
        self.draft = copy.deepcopy(self.original)
        self.layer = self.config.get("layer", "front")
        self.loading = True
        self.layer_combo.setCurrentIndex(max(0, self.layer_combo.findData(self.layer)))
        self.loading = False
        self.select_species(self.species_list.currentItem())

    def apply(self):
        if not self.quantity.hasAcceptableInput():
            self.status.setText(f"Informe uma quantidade inteira de 0 a {MAX_PETS}.")
            self.quantity.setFocus()
            return False
        if sum(self.active_count(e) for e in self.draft['pets']) > MAX_PETS:
            self.show_limit_notice()
            return False
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
                    target = entries.setdefault(entry["species"], copy.deepcopy(entry))
                    target.update({key: copy.deepcopy(entry[key]) for key in FIELDS if key in entry})
                current["pets"] = list(entries.values())
                if sum(self.active_count(e) for e in current['pets']) > MAX_PETS:
                    raise ValueError(f"Limite de {MAX_PETS} pets no total. Remova um pet antes de adicionar outro.")
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
