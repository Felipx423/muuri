"""Immediate pet controls for the tray, using the existing saved preferences."""
import copy

from PyQt6 import QtCore, QtGui, QtWidgets

from . import config_io
from .pets import PETS_DATA
from .petworker import MAX_PETS


class TrayPets:
    def __init__(self, owner):
        self.owner = owner
        self.visible_actions = {}
        self.remove_all_action = QtGui.QAction("Remover todos os pets", owner)
        self.remove_all_action.triggered.connect(self.remove_all)
        self.favorites_menu = QtWidgets.QMenu("Favoritos", owner)
        self.favorites_menu.setToolTipsVisible(True)
        self.choose_menu = QtWidgets.QMenu("Escolher favoritos", self.favorites_menu)
        self.choose_menu.setToolTipsVisible(True)
        self.favorites_menu.aboutToShow.connect(self.rebuild)

    def rebuild(self):
        self.favorites_menu.clear()
        self.choose_menu.clear()
        self.visible_actions = {}
        try:
            document = config_io.read_json(config_io.LIST_FILE)
        except (OSError, ValueError) as error:
            action = self.favorites_menu.addAction("Não foi possível ler os favoritos")
            action.setEnabled(False)
            action.setToolTip(str(error))
            return
        favorites = document.get("favorite_species", [])
        if not isinstance(favorites, list):
            favorites = []
        collection = self.owner.panel.species_list
        species_order = [collection.item(index).data(QtCore.Qt.ItemDataRole.UserRole)
                         for index in range(collection.count())]
        favorites = [species for species in species_order if species in favorites]
        for species in favorites:
            action = self.favorites_menu.addAction(species.capitalize())
            action.setCheckable(True)
            action.setToolTip("Marque para mostrar na tela; desmarque para retirar todas as cópias desta espécie.")
            action.triggered.connect(lambda checked, name=species: self.set_visible(name, checked))
            self.visible_actions[species] = action
        if not favorites:
            action = self.favorites_menu.addAction("Nenhum favorito selecionado")
            action.setEnabled(False)
        self.favorites_menu.addSeparator()
        self.favorites_menu.addMenu(self.choose_menu)
        for species in species_order:
            action = self.choose_menu.addAction(species.capitalize())
            action.setCheckable(True)
            action.setChecked(species in favorites)
            action.setToolTip("Salva o favorito sem alterar os pets na tela.")
            action.triggered.connect(lambda checked, name=species: self.set_favorite(name, checked))
        self.update_actions()

    def update_actions(self):
        active = {pet.species for pet in self.owner.pets}
        self.remove_all_action.setEnabled(bool(active))
        for species, action in self.visible_actions.items():
            action.setChecked(species in active)

    def set_favorite(self, species, favorite):
        def change(document):
            favorites = document.get("favorite_species", [])
            if not isinstance(favorites, list):
                favorites = []
            favorites = [name for name in favorites if name != species]
            if favorite:
                favorites.append(species)
            document["favorite_species"] = favorites
        return self.save(change, refresh=False)

    def set_visible(self, species, visible):
        def change(document):
            entries = document["pets"]
            entry = next((pet for pet in entries if pet["species"] == species), None)
            if entry is None:
                data = PETS_DATA[species]
                interactive = "drag" in data["states"][data["colors"][0]]
                entry = {"species": species, "colors": [], "enabled": False, "size": "Original",
                         "draggable": interactive, "settings_clicks": 4 if interactive else 0}
                entries.append(entry)
            entry["enabled"] = visible
            if visible:
                if not entry.get("colors"):
                    entry["colors"] = [PETS_DATA[species]["colors"][0]]
                if entry.get("count", 1) == 0:
                    entry["count"] = 1
                if sum(self.owner.panel.active_count(pet) for pet in entries) > MAX_PETS:
                    raise ValueError(f"Limite de {MAX_PETS} pets no total. Retire um pet antes de mostrar este favorito.")
            return {species: visible}
        return self.save(change)

    def remove_all(self):
        def change(document):
            for entry in document["pets"]:
                entry["enabled"] = False
            return {entry["species"]: False for entry in
                    document["pets"] + self.owner.panel.draft["pets"]}
        return self.save(change)

    def save(self, change, refresh=True):
        try:
            before = config_io.read_json(config_io.LIST_FILE)
            document = copy.deepcopy(before)
            visibility = change(document)
            if document != before:
                config_io.write_configs({config_io.LIST_FILE: document})
                if refresh:
                    try:
                        if not self.owner.start_refresh():
                            raise RuntimeError("Não foi possível atualizar os pets.")
                    except Exception:
                        config_io.write_configs({config_io.LIST_FILE: before})
                        self.owner.start_refresh()
                        raise
            self.owner.panel.sync_tray_changes(document, before, visibility)
            self.update_actions()
            return True
        except Exception as error:
            self.update_actions()
            QtWidgets.QMessageBox.warning(self.owner, "Não foi possível alterar os pets", str(error))
            return False
