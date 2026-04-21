import json
import os
import threading
from aqt import mw, gui_hooks
from aqt.qt import (
    QWidget, QVBoxLayout, QTextEdit, QLabel,
    Qt, QAction, QKeySequence, QMenu, QFormLayout, QLineEdit, QPushButton, QHBoxLayout,
    QDialog
)
from aqt.utils import tooltip, askUser

addon_dir = os.path.dirname(__file__)
config_file = os.path.join(addon_dir, "config.json")

MIRROR_CONFIG = {
    "fields": ["Front", "Back"],
    "show_on_question": True,
    "show_on_answer": True,
    "opacity": 1.0,
    "background_color": "#1a1a1a",
    "font_size": 16,
    "font_family": "Sans",
    "text_color": "#ffffff",
    "window_width": 300,
    "window_height": 200,
    "window_x": 100,
    "window_y": 100,
    "always_on_top": True,
    "frameless": True,
    "toggle_shortcut": "Ctrl+Shift+M"
}

HOTKEY_CONFIG = {
    "again": "f1",
    "hard": "f2",
    "good": "f3",
    "easy": "f4",
    "flip": "f5",
    "audio": "f6",
}

mirror_config = MIRROR_CONFIG.copy()
hotkey_config = HOTKEY_CONFIG.copy()

card_mirror_window = None
review_state = {"active": False, "showing_answer": False}


def get_config():
    global mirror_config, hotkey_config
    try:
        cfg = mw.addonManager.getConfig(__name__)
        if cfg and isinstance(cfg, dict):
            mirror_config.update(cfg.get("mirror", {}))
            hotkey_config.update(cfg.get("hotkeys", {}))
    except:
        pass
    for key, val in MIRROR_CONFIG.items():
        mirror_config.setdefault(key, val)
    for key, val in HOTKEY_CONFIG.items():
        hotkey_config.setdefault(key, val)
    return mirror_config, hotkey_config


def save_config():
    full_cfg = {
        "mirror": mirror_config,
        "hotkeys": hotkey_config
    }
    mw.addonManager.writeConfig(__name__, full_cfg)


def save_window_geometry():
    if card_mirror_window and card_mirror_window.isVisible():
        mirror_config["window_x"] = card_mirror_window.x()
        mirror_config["window_y"] = card_mirror_window.y()
        mirror_config["window_width"] = card_mirror_window.width()
        mirror_config["window_height"] = card_mirror_window.height()
        save_config()


KEYCODE_MAP = {
    "f1": 122, "f2": 120, "f3": 99, "f4": 96, "f5": 97, "f6": 98,
    "f7": 100, "f8": 101, "f9": 109, "f10": 103, "f11": 111, "f12": 105,
    "space": 49, "return": 36, "escape": 53,
    "1": 18, "2": 19, "3": 20, "4": 21, "5": 23, "6": 22, "7": 26, "8": 28, "9": 25, "0": 29,
    "a": 0, "b": 11, "c": 8, "d": 2, "e": 14, "f": 3, "g": 5, "h": 4, "i": 34, "j": 38, "k": 40, "l": 37, "m": 46, "n": 45, "o": 31, "p": 35, "q": 12, "r": 15, "s": 1, "t": 17, "u": 32, "v": 9, "w": 13, "x": 7, "y": 16, "z": 6,
    "command": 55, "shift": 56, "control": 59, "option": 58,
}


def get_keycode(key):
    key = key.lower().strip()
    return KEYCODE_MAP.get(key)


class CardMirrorWindow(QWidget):
    def __init__(self):
        get_config()

        flags = Qt.WindowType.Widget
        if mirror_config.get("always_on_top", True):
            flags |= Qt.WindowType.WindowStaysOnTopHint
        if mirror_config.get("frameless", True):
            flags |= Qt.WindowType.FramelessWindowHint

        super().__init__(None, flags)

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground,
                       mirror_config.get("background_color", "#1a1a1a") == "transparent")

        self.setStyleSheet(f"""
            QWidget {{
                background-color: {mirror_config.get("background_color", "#1a1a1a")};
            }}
            QTextEdit {{
                background-color: transparent;
                border: none;
                color: {mirror_config.get("text_color", "#ffffff")};
                font-size: {mirror_config.get("font_size", 16)}px;
                font-family: {mirror_config.get("font_family", "Sans")};
                padding: 10px;
            }}
            QLabel {{
                color: {mirror_config.get("text_color", "#ffffff")};
                background-color: transparent;
                padding: 5px;
            }}
        """)

        self.setWindowOpacity(mirror_config.get("opacity", 1.0))

        self.setGeometry(
            mirror_config.get("window_x", 100),
            mirror_config.get("window_y", 100),
            mirror_config.get("window_width", 300),
            mirror_config.get("window_height", 200)
        )

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(5, 5, 5, 5)
        self.setLayout(self.main_layout)

        self.content_widget = QTextEdit(self)
        self.content_widget.setReadOnly(True)
        self.content_widget.setTextInteractionFlags(Qt.TextInteractionFlag(0))
        self.main_layout.addWidget(self.content_widget)

        self._drag_position = None
        self._resize_position = None
        self._is_resizing = False
        self._is_dragging = False
        self._resize_margin = 10

        self.hide()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.globalPosition().toPoint()
            local_pos = event.position().toPoint()

            if (local_pos.x() >= self.width() - self._resize_margin or
                local_pos.y() >= self.height() - self._resize_margin):
                self._is_resizing = True
                self._resize_position = pos
            else:
                self._is_dragging = True
                self._drag_position = pos - self.pos()

            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            pos = event.globalPosition().toPoint()

            if self._is_resizing and self._resize_position:
                delta = pos - self._resize_position
                new_width = max(100, self.width() + delta.x())
                new_height = max(80, self.height() + delta.y())
                self.resize(int(new_width), int(new_height))
                self._resize_position = pos
                event.accept()
            elif self._is_dragging and self._drag_position:
                new_pos = pos - self._drag_position
                self.move(new_pos)
                event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self._is_resizing or self._is_dragging:
                save_window_geometry()
            self._is_resizing = False
            self._is_dragging = False
            self._resize_position = None
            self._drag_position = None

    def showEvent(self, event):
        self.activateWindow()
        super().showEvent(event)

    def update_style(self):
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {mirror_config.get("background_color", "#1a1a1a")};
            }}
            QTextEdit {{
                background-color: transparent;
                border: none;
                color: {mirror_config.get("text_color", "#ffffff")};
                font-size: {mirror_config.get("font_size", 16)}px;
                font-family: {mirror_config.get("font_family", "Sans")};
                padding: 10px;
            }}
            QLabel {{
                color: {mirror_config.get("text_color", "#ffffff")};
                background-color: transparent;
                padding: 5px;
            }}
        """)
        self.setWindowOpacity(mirror_config.get("opacity", 1.0))

    def update_content(self, card, showing_answer=None):
        if not card:
            self.content_widget.clear()
            return

        if showing_answer is None:
            showing_answer = review_state.get("showing_answer", False)

        all_fields = mirror_config.get("fields", ["Front", "Back"])

        if showing_answer:
            if not mirror_config.get("show_on_answer", True):
                self.content_widget.clear()
                return
            fields_to_show = all_fields
        else:
            if not mirror_config.get("show_on_question", True):
                self.content_widget.clear()
                return
            fields_to_show = all_fields[:1]

        note = card.note()
        html_parts = []

        for field_name in fields_to_show:
            if field_name in note:
                field_value = note[field_name]
                if field_value:
                    html_parts.append(f'<div class="field-{field_name}">{field_value}</div>')

        if html_parts:
            self.content_widget.setHtml('\n'.join(html_parts))
        else:
            self.content_widget.clear()

        if self.isHidden():
            self.show()

    def toggle_visibility(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()


def create_mirror_window():
    global card_mirror_window
    if card_mirror_window is None:
        card_mirror_window = CardMirrorWindow()
    return card_mirror_window


def get_mirror_window():
    return card_mirror_window


def on_show_question(card):
    get_config()
    window = get_mirror_window()
    if window:
        window.update_content(card, showing_answer=False)
    review_state["showing_answer"] = False


def on_show_answer(card):
    get_config()
    window = get_mirror_window()
    if window:
        window.update_content(card, showing_answer=True)
    review_state["showing_answer"] = True


def answer_card(button):
    def do_answer():
        try:
            mw.taskman.run_on_main(lambda: _do_answer(button))
        except:
            pass

    thread = threading.Thread(target=do_answer)
    thread.start()


def _do_answer(button):
    try:
        reviewer = mw.reviewer
        if reviewer is None:
            return

        if not hasattr(reviewer, 'card') or reviewer.card is None:
            return

        if mw.state != "review":
            return

        reviewer._answerCard(button)
    except Exception as e:
        pass


def flip_card():
    def do_flip():
        try:
            mw.taskman.run_on_main(lambda: _flip_card())
        except:
            pass

    thread = threading.Thread(target=do_flip)
    thread.start()


def _flip_card():
    try:
        reviewer = mw.reviewer
        if reviewer is None:
            return

        if not hasattr(reviewer, 'card') or reviewer.card is None:
            return

        if mw.state != "review":
            return

        reviewer._showAnswer()
        review_state["showing_answer"] = True

        window = get_mirror_window()
        if window and hasattr(reviewer, 'card') and reviewer.card:
            window.update_content(reviewer.card, showing_answer=True)
    except:
        pass


def replay_audio():
    def do_audio():
        try:
            mw.taskman.run_on_main(lambda: _replay_audio())
        except:
            pass

    thread = threading.Thread(target=do_audio)
    thread.start()


def _replay_audio():
    try:
        reviewer = mw.reviewer
        if reviewer is None:
            return

        if not hasattr(reviewer, 'card') or reviewer.card is None:
            return

        if mw.state != "review":
            return

        if hasattr(reviewer, 'replayAudio'):
            reviewer.replayAudio()
        elif hasattr(reviewer, 'onReplay'):
            reviewer.onReplay()
    except:
        pass


def load_hotkey_config():
    try:
        if os.path.exists(config_file):
            with open(config_file, "r") as f:
                data = json.load(f)
                if "hotkeys" in data:
                    hotkey_config.update(data["hotkeys"])
                elif "again" in data:
                    for k, v in data.items():
                        if k in hotkey_config:
                            hotkey_config[k] = v
                for key, val in HOTKEY_CONFIG.items():
                    hotkey_config.setdefault(key, val)
    except Exception as e:
        print(f"Error loading config: {e}")

def register_hotkeys():
    try:
        import Quartz

        key_again = get_keycode(hotkey_config.get("again", "f1"))
        key_hard = get_keycode(hotkey_config.get("hard", "f2"))
        key_good = get_keycode(hotkey_config.get("good", "f3"))
        key_easy = get_keycode(hotkey_config.get("easy", "f4"))
        key_flip = get_keycode(hotkey_config.get("flip", "f5"))
        key_audio = get_keycode(hotkey_config.get("audio", "f6"))

        print(f"Registering hotkeys: again={key_again}, hard={key_hard}, good={key_good}, easy={key_easy}, flip={key_flip}, audio={key_audio}")

        def callback(proxy, type, event, refcon):
            if type == Quartz.kCGEventKeyDown:
                key_code = Quartz.CGEventGetIntegerValueField(event, Quartz.kCGKeyboardEventKeycode)
                if key_code == key_again:
                    print(f"Hotkey: Again (keycode {key_code})")
                    answer_card(1)
                elif key_code == key_hard:
                    print(f"Hotkey: Hard (keycode {key_code})")
                    answer_card(2)
                elif key_code == key_good:
                    print(f"Hotkey: Good (keycode {key_code})")
                    answer_card(3)
                elif key_code == key_easy:
                    print(f"Hotkey: Easy (keycode {key_code})")
                    answer_card(4)
                elif key_code == key_flip:
                    print(f"Hotkey: Flip (keycode {key_code})")
                    flip_card()
                elif key_code == key_audio:
                    print(f"Hotkey: Audio (keycode {key_code})")
                    replay_audio()
            return event

        def runlistener():
            source = Quartz.CGEventSourceCreate(Quartz.kCGEventSourceStateHIDSystemState)
            tap = Quartz.CGEventTapCreate(
                Quartz.kCGSessionEventTap,
                Quartz.kCGHeadInsertEventTap,
                Quartz.kCGEventTapOptionListenOnly,
                Quartz.CGEventMaskBit(Quartz.kCGEventKeyDown),
                callback,
                source
            )

            if tap:
                print("CGEventTap created successfully")
                run_loop = Quartz.CFRunLoopGetCurrent()
                Quartz.CFRunLoopAddSource(
                    run_loop,
                    Quartz.CFMachPortCreateRunLoopSource(None, tap, 0),
                    Quartz.kCFRunLoopCommonModes
                )
                Quartz.CGEventTapEnable(tap, True)
                Quartz.CFRunLoopRun()
            else:
                print("Failed to create event tap - check Accessibility permissions")

        thread = threading.Thread(target=runlistener, daemon=True)
        thread.start()

    except Exception as e:
        print(f"Failed to register hotkeys: {e}")
        import traceback
        traceback.print_exc()


class FieldsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent or mw)
        self.setWindowTitle("SetFields")
        self.setModal(True)
        self.resize(350, 300)
        self.setup_ui()
        self.load_values()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.fields_edit = QLineEdit(self)
        self.bg_color_edit = QLineEdit(self)
        self.text_color_edit = QLineEdit(self)
        self.font_size_edit = QLineEdit(self)
        self.opacity_edit = QLineEdit(self)

        form.addRow("Fields (comma sep):", self.fields_edit)
        form.addRow("Background:", self.bg_color_edit)
        form.addRow("Text color:", self.text_color_edit)
        form.addRow("Font size:", self.font_size_edit)
        form.addRow("Opacity (0-1):", self.opacity_edit)

        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Save", self)
        cancel_btn = QPushButton("Cancel", self)
        save_btn.clicked.connect(self.save)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def load_values(self):
        self.fields_edit.setText(", ".join(mirror_config.get("fields", ["Front", "Back"])))
        self.bg_color_edit.setText(mirror_config.get("background_color", "#1a1a1a"))
        self.text_color_edit.setText(mirror_config.get("text_color", "#ffffff"))
        self.font_size_edit.setText(str(mirror_config.get("font_size", 16)))
        self.opacity_edit.setText(str(mirror_config.get("opacity", 1.0)))

    def save(self):
        global mirror_config

        fields_text = self.fields_edit.text()
        mirror_config["fields"] = [f.strip() for f in fields_text.split(",") if f.strip()]
        mirror_config["background_color"] = self.bg_color_edit.text()
        mirror_config["text_color"] = self.text_color_edit.text()
        try:
            mirror_config["font_size"] = int(self.font_size_edit.text())
        except:
            pass
        try:
            mirror_config["opacity"] = float(self.opacity_edit.text())
        except:
            pass

        save_config()

        if card_mirror_window:
            card_mirror_window.update_style()
            card_mirror_window.show()
            window = get_mirror_window()
            if window:
                window.update_content(getattr(mw.reviewer, 'card', None), True)

        tooltip("Fields saved!")
        self.accept()


class HotkeysDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent or mw)
        self.setWindowTitle("SetHotkeys")
        self.setModal(True)
        self.resize(300, 250)
        self.setup_ui()
        self.load_values()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.again_edit = QLineEdit(self)
        self.hard_edit = QLineEdit(self)
        self.good_edit = QLineEdit(self)
        self.easy_edit = QLineEdit(self)
        self.flip_edit = QLineEdit(self)
        self.audio_edit = QLineEdit(self)

        form.addRow("Again:", self.again_edit)
        form.addRow("Hard:", self.hard_edit)
        form.addRow("Good:", self.good_edit)
        form.addRow("Easy:", self.easy_edit)
        form.addRow("Flip:", self.flip_edit)
        form.addRow("Audio:", self.audio_edit)

        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Save", self)
        cancel_btn = QPushButton("Cancel", self)
        save_btn.clicked.connect(self.save)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def load_values(self):
        self.again_edit.setText(hotkey_config.get("again", "f1"))
        self.hard_edit.setText(hotkey_config.get("hard", "f2"))
        self.good_edit.setText(hotkey_config.get("good", "f3"))
        self.easy_edit.setText(hotkey_config.get("easy", "f4"))
        self.flip_edit.setText(hotkey_config.get("flip", "f5"))
        self.audio_edit.setText(hotkey_config.get("audio", "f6"))

    def save(self):
        global hotkey_config

        hotkey_config["again"] = self.again_edit.text().lower()
        hotkey_config["hard"] = self.hard_edit.text().lower()
        hotkey_config["good"] = self.good_edit.text().lower()
        hotkey_config["easy"] = self.easy_edit.text().lower()
        hotkey_config["flip"] = self.flip_edit.text().lower()
        hotkey_config["audio"] = self.audio_edit.text().lower()

        save_config()
        register_hotkeys()

        tooltip("Hotkeys saved!")
        self.accept()


def show_hotkeys():
    get_config()
    dialog = HotkeysDialog(mw)
    dialog.exec()


def show_fields():
    get_config()
    dialog = FieldsDialog(mw)
    dialog.exec()


def add_menu():
    try:
        menubar = mw.form.menubar
        menu = QMenu("Review While Gaming", mw)

        hotkeys_action = QAction("SetHotkeys", mw)
        hotkeys_action.triggered.connect(show_hotkeys)
        menu.addAction(hotkeys_action)

        fields_action = QAction("SetFields", mw)
        fields_action.triggered.connect(show_fields)
        menu.addAction(fields_action)

        menu.addSeparator()

        toggle_action = QAction("Toggle Mirror", mw)
        toggle_action.setShortcut(QKeySequence(mirror_config.get("toggle_shortcut", "Ctrl+Shift+M")))
        toggle_action.triggered.connect(lambda: get_mirror_window().toggle_visibility() if get_mirror_window() else None)
        menu.addAction(toggle_action)

        menubar.addMenu(menu)
    except:
        pass


def on_unload():
    save_window_geometry()


def on_config_changed(manager):
    from aqt.qt import QTimer
    def reload():
        get_config()
        if card_mirror_window and card_mirror_window.isVisible():
            card_mirror_window.update_style()
        register_hotkeys()
    QTimer.singleShot(200, reload)


def on_main_window_did_init():
    get_config()
    load_hotkey_config()
    create_mirror_window()
    add_menu()
    gui_hooks.reviewer_did_show_question.append(on_show_question)
    gui_hooks.reviewer_did_show_answer.append(on_show_answer)
    register_hotkeys()


gui_hooks.main_window_did_init.append(on_main_window_did_init)