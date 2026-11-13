"""Jarvis desktop widgets and background job coordination."""
import asyncio
from html import escape
from pathlib import Path
import ctypes
import json
import sys
import threading

import httpx
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QIcon, QAction, QCursor, QKeySequence, QPainter, QTextCursor
from PySide6.QtWidgets import (
    QApplication, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QFrame, QHBoxLayout, QInputDialog, QLabel,
    QListWidget, QListWidgetItem, QMainWindow, QMenu, QMessageBox, QPlainTextEdit,
    QProgressBar, QPushButton, QStyle, QStyleOptionComboBox, QTextBrowser, QVBoxLayout, QWidget,
)

from .backend import CONTEXT_SIZES, MODEL_FOLDER, SETTINGS_PATH, Ollama, load_context_size, save_context_size, save_settings
from .chat import ChatService, memory_request
from .memory_dialog import MemoryDialog

STYLE = """
QMainWindow, QWidget#main { background: #191a20; color: #ececf2; }
QWidget { font-family: 'Inter', 'Segoe UI'; font-size: 14px; color: #ececf2; }
QFrame#sidebar { background: #14151b; border-right: 1px solid #2c2d37; }
QLabel#brand { font-size: 24px; font-weight: 650; }
QLabel#title { font-size: 16px; font-weight: 600; }
QLabel#muted, QLabel#status { color: #a7a9bb; font-size: 12px; }
QLabel#status[error="true"] { color: #f7aeb4; }
QPushButton, QComboBox { border: 1px solid #353747; background: #252631;
    border-radius: 8px; padding: 7px 12px; min-height: 20px; }
QPushButton:hover, QComboBox:hover { background: #333548; }
QPushButton:focus, QComboBox:focus, QPlainTextEdit:focus { border-color: #9e9aff; }
QPushButton:disabled, QComboBox:disabled { color: #85889c; background: #22232b; }
QPushButton#primary { background: #aaa3ff; color: #171425; font-weight: 650; }
QPushButton#primary:hover { background: #c0baff; }
QPushButton#primary:disabled { background: #39364d; color: #b0a9ca; }
QComboBox QAbstractItemView { background: #252631; selection-background-color: #49446d; }
QListWidget, QTextBrowser { border: none; background: transparent; }
QListWidget::item { padding: 10px 8px; border-radius: 7px; }
QListWidget::item:selected { background: #303046; color: #fff; }
QListWidget::item:hover:!selected { background: #22232e; }
QPlainTextEdit { background: #22232c; border: 1px solid #36384a; border-radius: 12px; padding: 10px; }
QScrollBar:vertical { background: transparent; width: 10px; }
QScrollBar::handle:vertical { background: #414354; border-radius: 5px; min-height: 20px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QMessageBox { background: #252631; }
"""


class Job(QThread):
    progress = Signal(object)
    outcome = Signal(str, object)

    def __init__(self, work, parent):
        super().__init__(parent)
        self.work = work
        self.cancelled = threading.Event()
        self.loop = None
        self.task = None

    def cancel(self):
        self.cancelled.set()
        if self.loop and self.task:
            try:
                self.loop.call_soon_threadsafe(self.task.cancel)
            except RuntimeError:
                pass  # The event loop already finished.

    def run(self):
        async def execute():
            self.loop = asyncio.get_running_loop()
            self.task = asyncio.current_task()
            if self.cancelled.is_set():
                raise asyncio.CancelledError
            return await self.work(self.progress.emit)
        try:
            result = asyncio.run(execute())
        except asyncio.CancelledError:
            self.outcome.emit("stopped", None)
        except (httpx.ConnectError, httpx.ConnectTimeout):
            self.outcome.emit("error", "Ollama is offline. Open Ollama, then refresh the model list.")
        except httpx.TimeoutException:
            self.outcome.emit("error", "Ollama took too long to respond. Try again or select a smaller model.")
        except Exception as error:
            self.outcome.emit("error", str(error))
        else:
            self.outcome.emit("complete", result)


class ModelPicker(QComboBox):
    text_flags = Qt.AlignmentFlag.AlignVCenter.value | Qt.TextFlag.TextWrapAnywhere.value

    def _text_area(self, option):
        return self.style().subControlRect(
            QStyle.ComplexControl.CC_ComboBox, option,
            QStyle.SubControl.SC_ComboBoxEditField, self,
        )

    def refresh_label(self):
        text = self.currentText() or self.placeholderText()
        self.setToolTip(text)
        option = QStyleOptionComboBox()
        self.initStyleOption(option)
        area = self._text_area(option)
        metrics = self.fontMetrics()
        text_height = metrics.boundingRect(0, 0, max(1, area.width()), 10000, self.text_flags, text).height()
        self.setMinimumHeight(max(self.sizeHint().height(), text_height + self.height() - area.height()))
        self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.refresh_label()

    def paintEvent(self, event):
        option = QStyleOptionComboBox()
        self.initStyleOption(option)
        painter = QPainter(self)
        self.style().drawComplexControl(QStyle.ComplexControl.CC_ComboBox, option, painter, self)
        painter.setPen("#ececf2" if self.isEnabled() else "#a7a9bb")
        painter.drawText(self._text_area(option), self.text_flags, self.currentText() or self.placeholderText())


class Composer(QPlainTextEdit):
    submit = Signal()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and event.modifiers() in (
            Qt.KeyboardModifier.NoModifier, Qt.KeyboardModifier.ControlModifier,
        ):
            self.submit.emit()
        else:
            super().keyPressEvent(event)


class Window(QMainWindow):
    def __init__(self, service: ChatService, backend: Ollama, settings_path=SETTINGS_PATH):
        super().__init__()
        self.service = service
        self.backend = backend
        self.chat_id = None
        self.job = None
        self.operation = None
        self.closing = False
        self.pending = ""
        self.actual_model = ""
        self.settings_path = settings_path
        self.saved_context = load_context_size(settings_path)
        preferences = json.loads(settings_path.read_text(encoding="utf-8"))
        self.default_model = preferences.get("default_model", "")
        self.thinking_modes = preferences.get("thinking_modes", {})
        self.request_context = None
        self.displayed_messages = []
        self.context_lengths = {}
        self.last_context = {}
        self.setWindowTitle("Jarvis Desktop")
        self.resize(1120, 760)
        self.setMinimumSize(720, 510)
        self.setStyleSheet(STYLE)
        self._build()
        self._sidebar()
        self.refresh_models()

    def _build(self):
        root = QWidget()
        root.setObjectName("main")
        self.setCentralWidget(root)
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(224)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(16, 22, 16, 16)
        side.setSpacing(14)
        brand = QLabel("Jarvis")
        brand.setObjectName("brand")
        side.addWidget(brand)
        self.new_button = QPushButton("+  New chat")
        self.new_button.clicked.connect(self.new_chat)
        side.addWidget(self.new_button)
        self.memory_button = QPushButton("Memory")
        self.memory_button.clicked.connect(self.open_memory)
        side.addWidget(self.memory_button)
        self.settings_button = QPushButton("Settings")
        self.settings_button.clicked.connect(self.open_settings)
        side.addWidget(self.settings_button)
        recent = QLabel("Recent chats")
        recent.setObjectName("muted")
        side.addWidget(recent)
        self.history = QListWidget()
        self.history.currentItemChanged.connect(self._open_chat)
        self.history.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.history.customContextMenuRequested.connect(self._chat_menu)
        side.addWidget(self.history, 1)
        self.hidden_button = QPushButton("Show hidden chats")
        self.hidden_button.setCheckable(True)
        self.hidden_button.toggled.connect(self._toggle_hidden)
        side.addWidget(self.hidden_button)
        layout.addWidget(sidebar)

        body = QWidget()
        pane = QVBoxLayout(body)
        pane.setContentsMargins(24, 20, 24, 16)
        pane.setSpacing(12)
        top = QHBoxLayout()
        self.title = QLabel("New chat")
        self.title.setObjectName("title")
        self.title.setTextFormat(Qt.TextFormat.PlainText)
        top.addWidget(self.title, 1)
        self.models = ModelPicker()
        self.models.setAccessibleName("Chat model")
        self.models.setMinimumWidth(0)
        self.models.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.models.view().setTextElideMode(Qt.TextElideMode.ElideNone)
        self.models.currentIndexChanged.connect(self._model_changed)
        self.refresh = QPushButton("Refresh")
        self.refresh.clicked.connect(self.refresh_models)
        top.addWidget(self.refresh)
        self.import_button = QPushButton("Import GGUF")
        self.import_button.clicked.connect(self.import_model)
        top.addWidget(self.import_button)
        pane.addLayout(top)
        pane.addWidget(self.models)
        self.transcript = QTextBrowser()
        self.transcript.setAccessibleName("Conversation")
        pane.addWidget(self.transcript, 1)
        self.composer = Composer()
        self.composer.setAccessibleName("Message")
        self.composer.setPlaceholderText("Message Jarvis")
        self.composer.setFixedHeight(88)
        self.composer.textChanged.connect(self._draft_changed)
        self.composer.submit.connect(self.send)
        pane.addWidget(self.composer)
        context_row = QHBoxLayout()
        self.context_label = QLabel()
        self.context_label.setObjectName("muted")
        self.context_label.setToolTip("The estimate covers chat text and your draft. "
                                      "Last turn adds Ollama's reported prompt and reply tokens.")
        context_row.addWidget(self.context_label)
        self.context_bar = QProgressBar()
        self.context_bar.setAccessibleName("Estimated context usage")
        self.context_bar.setFixedSize(90, 7)
        self.context_bar.setTextVisible(False)
        context_row.addWidget(self.context_bar)
        context_row.addStretch()
        context_row.addWidget(QLabel("Context size"))
        self.context_picker = QComboBox()
        self.context_picker.setAccessibleName("Context size for the next request")
        self.context_picker.setToolTip("Applied on the next reply. Saved after a successful request.")
        for size in CONTEXT_SIZES:
            self.context_picker.addItem(f"{size // 1024}K", size)
        self.context_picker.setCurrentIndex(self.context_picker.findData(self.saved_context))
        self.context_picker.currentIndexChanged.connect(self._update_context)
        context_row.addWidget(self.context_picker)
        pane.addLayout(context_row)
        footer = QHBoxLayout()
        self.status = QLabel()
        self.status.setObjectName("status")
        self.status.setTextFormat(Qt.TextFormat.PlainText)
        self.status.setWordWrap(True)
        footer.addWidget(self.status, 1)
        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.stop)
        footer.addWidget(self.stop_button)
        self.send_button = QPushButton("Send")
        self.send_button.setObjectName("primary")
        self.send_button.clicked.connect(self.send)
        footer.addWidget(self.send_button)
        pane.addLayout(footer)
        layout.addWidget(body, 1)
        new_shortcut = QAction(self)
        new_shortcut.setShortcut(QKeySequence("Ctrl+N"))
        new_shortcut.triggered.connect(self.new_chat)
        self.addAction(new_shortcut)

    def _sidebar(self):
        include_hidden = self.hidden_button.isChecked()
        rows = self.service.chats(include_hidden)
        if not rows:
            self.chat_id = self.service.create("")
            rows = self.service.chats(include_hidden)
        if not any(row["id"] == self.chat_id for row in rows):
            self.chat_id = rows[0]["id"]
        self.history.blockSignals(True)
        self.history.clear()
        for row in rows:
            item = QListWidgetItem(f'{row["title"]} (hidden)' if row["hidden"] else row["title"])
            item.setToolTip(row["title"])
            item.setData(Qt.ItemDataRole.UserRole, row["id"])
            self.history.addItem(item)
            if row["id"] == self.chat_id:
                self.history.setCurrentItem(item)
        self.history.blockSignals(False)
        self._open_chat(self.history.currentItem())

    def _open_chat(self, item, previous=None):
        if item is None:
            return
        self.chat_id = item.data(Qt.ItemDataRole.UserRole)
        row = next(row for row in self.service.chats(self.hidden_button.isChecked()) if row["id"] == self.chat_id)
        self.title.setText(row["title"])
        self.composer.blockSignals(True)
        self.composer.setPlainText(row["draft"])
        self.composer.blockSignals(False)
        self._select_saved_model(row["model"])
        self.displayed_messages = self.service.messages(self.chat_id)
        self._render()
        self._buttons()

    def _toggle_hidden(self, show):
        self.hidden_button.setText("Hide hidden chats" if show else "Show hidden chats")
        self._sidebar()

    def _chat_menu(self, position):
        item = self.history.itemAt(position)
        if self.job or item is None:
            return
        chat_id = item.data(Qt.ItemDataRole.UserRole)
        row = next(row for row in self.service.chats(self.hidden_button.isChecked()) if row["id"] == chat_id)
        menu = QMenu(self)
        rename = menu.addAction("Rename chat")
        visibility = menu.addAction("Restore chat" if row["hidden"] else "Hide chat")
        action = menu.exec(self.history.viewport().mapToGlobal(position))
        if action == rename:
            title, accepted = QInputDialog.getText(self, "Rename chat", "Title", text=row["title"])
            if accepted:
                try:
                    self.service.rename_chat(chat_id, title)
                except ValueError as error:
                    self._set_status(str(error), True)
                    return
                self._sidebar()
        elif action == visibility:
            self.service.set_chat_hidden(chat_id, not row["hidden"])
            if not row["hidden"] and self.chat_id == chat_id:
                self.chat_id = None
            self._sidebar()

    def _select_saved_model(self, saved):
        index = self.models.findData(saved)
        if index < 0 and not saved and self.models.count():
            index = self.models.findData(self.default_model)
            if index < 0:
                index = self.models.findData("jarvis-qwen3-5-9b-uncensored-hauhaucs-aggressive-q4-k-m:latest")
            if index < 0:
                index = max(0, self.models.findData("qwen3.5:0.8b"))
        self.models.blockSignals(True)
        self.models.setCurrentIndex(index)
        self.models.setPlaceholderText(f"Unavailable: {saved}" if saved else "Choose a model")
        self.models.blockSignals(False)
        if not saved and index >= 0:
            self.service.select_model(self.chat_id, self.models.currentData())

    def _model_changed(self):
        if self.chat_id and self.models.currentData():
            self.service.select_model(self.chat_id, self.models.currentData())
        self._buttons()

    def _draft_changed(self):
        self.service.save_draft(self.chat_id, self.composer.toPlainText())
        self._buttons()

    def open_memory(self):
        MemoryDialog(self.service.memory, self.chat_id, self).exec()

    def open_settings(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Jarvis Settings")
        form = QFormLayout(dialog)
        default_model = QComboBox(dialog)
        default_model.addItem("Automatic", "")
        for index in range(self.models.count()):
            name = self.models.itemData(index)
            default_model.addItem(name, name)
        if self.default_model and default_model.findData(self.default_model) < 0:
            default_model.addItem(f"{self.default_model} (unavailable)", self.default_model)
        default_model.setCurrentIndex(default_model.findData(self.default_model))
        form.addRow("Default model for new chats", default_model)
        context = QComboBox(dialog)
        for size in CONTEXT_SIZES:
            context.addItem(f"{size // 1024}K", size)
        context.setCurrentIndex(context.findData(self.context_picker.currentData()))
        context.setToolTip("A new context size is saved after Ollama accepts it.")
        form.addRow("Context for next reply", context)
        model = self.models.currentData()
        thinking = None
        values = self.backend.thinking_values(model) if model else ()
        if any(value is True or isinstance(value, str) for value in values):
            thinking = QComboBox(dialog)
            thinking.addItem("Model default", None)
            for value in values:
                thinking.addItem({True: "On", False: "Off"}.get(value, str(value).title()), value)
            thinking.setCurrentIndex(max(0, thinking.findData(self.thinking_modes.get(model))))
            form.addRow("Thinking for selected model", thinking)
        if "tools" in getattr(self.backend, "model_info", {}).get(model, {}).get("capabilities", ()):
            form.addRow("Tools", QLabel("Unavailable in Jarvis Desktop"))
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)
        if not dialog.exec():
            return
        modes = dict(self.thinking_modes)
        if thinking is not None:
            modes[model] = thinking.currentData()
        try:
            save_settings(self.settings_path, default_model=default_model.currentData(), thinking_modes=modes)
        except (OSError, ValueError) as error:
            self._set_status(f"Settings could not be saved. {error}", True)
            return
        self.default_model = default_model.currentData()
        self.thinking_modes = modes
        self.context_picker.setCurrentIndex(self.context_picker.findData(context.currentData()))

    def new_chat(self):
        if self.job is None:
            model = self.default_model if self.models.findData(self.default_model) >= 0 else self.models.currentData()
            self.chat_id = self.service.create(model or "")
            self._sidebar()
            self.composer.setFocus()

    def _render(self):
        def message(role, content, model, status):
            label = "You" if role == "user" else "Jarvis"
            if model:
                label += " · " + model
            if status in ("stopped", "error"):
                label += " · " + ("Stopped" if status == "stopped" else "Interrupted")
            empty = "Waiting for the model…" if status == "pending" else "No reply was generated."
            body = escape(content or empty).replace("\n", "<br>")
            return (f'<p style="color:#aaa6ed; font-weight:600; margin-top:18px;">{escape(label)}</p>'
                    f'<p style="color:#ececf2; line-height:150%;">{body}</p>')

        blocks = [message(row["role"], row["content"], row["model"], row["status"])
                  for row in self.displayed_messages]
        if any(row["archived"] for row in self.displayed_messages):
            blocks.insert(0, '<p style="color:#aaa6ed;">Messages from before the memory reset '
                             'are shown here for reference and excluded from new replies.</p>')
        if self.operation == "chat":
            blocks.append(message("assistant", self.pending, self.actual_model, "pending"))
        self.transcript.setHtml("".join(blocks) or
            '<h2 style="color:#ececf2; margin-top:36px;">How can I help?</h2>')
        self.transcript.moveCursor(QTextCursor.MoveOperation.End)

    def _buttons(self):
        self._update_context()
        busy = self.job is not None
        for widget in (self.new_button, self.memory_button, self.settings_button, self.history, self.hidden_button,
                       self.models, self.refresh, self.import_button):
            widget.setEnabled(not busy)
        self.context_picker.setEnabled(not busy)
        self.models.refresh_label()
        draft = self.composer.toPlainText().strip()
        self.send_button.setEnabled(not busy and bool(draft)
                                    and bool(self.models.currentData() or memory_request(draft)))
        self.stop_button.setVisible(self.operation == "chat")
        self.stop_button.setEnabled(self.operation == "chat")

    def _update_context(self):
        model = self.models.currentData()
        draft = self.composer.toPlainText()
        messages = [row["content"] for row in self.displayed_messages if row["content"] and not row["archived"]]
        if self.operation == "chat" and self.pending:
            messages.append(self.pending)
        if draft:
            messages.append(draft)
        estimate = sum((len(message.encode("utf-8")) + 3) // 4 + 4 for message in messages)
        limit = self.context_picker.currentData()
        label = f"Chat ≈ {estimate:,} / {limit:,} selected"
        percent = round(100 * estimate / limit)
        self.context_bar.setValue(min(percent, 100))
        color = "#f19a9a" if percent >= 95 else "#e9b872" if percent >= 80 else "#aaa3ff"
        self.context_bar.setStyleSheet(
            "QProgressBar { background: #353747; border: none; border-radius: 3px; }"
            f"QProgressBar::chunk {{ background: {color}; border-radius: 3px; }}"
        )
        verified = self.context_lengths.get(model)
        if verified is not None:
            label += f" · Last verified {verified // 1024}K"
        last = self.last_context.get((self.chat_id, model))
        if last is not None:
            label += f" · Last turn {last:,}"
        self.context_label.setText(label)

    def _set_status(self, message, error=False):
        self.status.setText(message)
        self.status.setProperty("error", error)
        self.status.style().unpolish(self.status)
        self.status.style().polish(self.status)

    def _start(self, kind, work, status):
        self.operation = kind
        self.job = Job(work, self)
        self.job.progress.connect(self._progress)
        self.job.outcome.connect(self._outcome)
        self.job.finished.connect(self._job_finished)
        self._set_status(status)
        self._buttons()
        self.job.start()

    def refresh_models(self):
        async def work(progress):
            return await self.backend.list_models()
        self._start("models", work, "Checking local models…")

    def import_model(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import a model", str(MODEL_FOLDER), "GGUF models (*.gguf)")
        if not path:
            return
        async def work(progress):
            tag = await self.backend.import_gguf(path, progress)
            return await self.backend.list_models(), tag
        self._start("import", work, "Checking the model file…")

    def send(self):
        draft = self.composer.toPlainText().strip()
        if self.job or not draft:
            return
        request = memory_request(draft)
        if request:
            saved = self.service.save_requested_memory(self.chat_id, draft, request)
            self.composer.clear()
            self._sidebar()
            self._set_status("Memory saved." if saved else "Memory save failed.", not saved)
            return
        model = self.models.currentData()
        if not model:
            return
        messages = self.service.begin(self.chat_id, draft)
        self.composer.clear()
        self.displayed_messages = self.service.messages(self.chat_id)
        self.pending = ""
        self.actual_model = ""
        size = self.context_picker.currentData()
        self.request_context = size
        think = self.thinking_modes.get(model)

        async def work(progress):
            effective = None
            stream = (self.backend.stream(model, messages, size) if think is None else
                      self.backend.stream(model, messages, size, think=think))
            async for chunk in stream:
                progress(chunk)
                if chunk.context_length is not None:
                    effective = chunk.context_length
            return effective
        self._start("chat", work, f"Loading {model} with {size // 1024}K context…")
        self._render()

    def stop(self):
        if self.job and self.operation == "chat":
            self.job.cancel()
            self.stop_button.setEnabled(False)
            self._set_status("Stopping…")

    def _progress(self, payload):
        if self.operation == "chat":
            self.pending += payload.text
            self.actual_model = payload.model or self.actual_model
            model = self.models.currentData()
            if payload.context_length:
                self._set_status(f"Generating with {model}…")
            if payload.prompt_tokens is not None and payload.reply_tokens is not None:
                self.last_context[self.chat_id, model] = payload.prompt_tokens + payload.reply_tokens
            self._update_context()
            if payload.text:
                self._render()
        else:
            self._set_status(str(payload))

    def _outcome(self, state, result):
        if self.operation == "chat":
            self.service.finish(self.chat_id, self.pending, self.actual_model, state)
            self._sidebar()
            size = self.request_context
            if state == "complete":
                if result is not None:
                    self.context_lengths[self.models.currentData()] = result
                if size != self.saved_context:
                    try:
                        save_context_size(self.settings_path, size)
                    except (OSError, ValueError) as error:
                        self._set_status(f"{size // 1024}K worked, but the setting could not be saved. {error}", True)
                        return
                    self.saved_context = size
                used = self.service.memory.used
                self._set_status("Memory included: " + ", ".join(used) if used else "Ready")
            else:
                self.context_picker.setCurrentIndex(self.context_picker.findData(self.saved_context))
                if state == "stopped":
                    self._set_status("Reply stopped.")
                else:
                    self._set_status(f"{size // 1024}K context request failed. {result}", True)
            return
        elif state == "complete":
            names, tag = result if self.operation == "import" else (result, None)
            self.models.blockSignals(True)
            self.models.clear()
            for name in names:
                self.models.addItem(name, name)
                self.models.setItemData(self.models.count() - 1, name, Qt.ItemDataRole.ToolTipRole)
            longest = max((self.models.view().fontMetrics().horizontalAdvance(name) for name in names), default=0)
            self.models.view().setMinimumWidth(longest + 40)
            self.models.blockSignals(False)
            if tag:
                self.service.select_model(self.chat_id, tag)
            self._sidebar()
            self._set_status(f"Imported {tag}" if tag else
                             "Ollama connected" if names else "Import a chat model to get started.")
        if state == "error":
            self._set_status(result, True)

    def _job_finished(self):
        self.job.wait()
        self.job.deleteLater()
        self.job = None
        self.operation = None
        self._buttons()
        self._render()
        if self.closing:
            self.close()

    def closeEvent(self, event):
        if self.job:
            self.closing = True
            self.job.cancel()
            event.ignore()
        else:
            self.service.db.close()
            event.accept()


def run():
    if sys.platform == "win32":
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Jarvis.Desktop")
    app = QApplication([])
    app.setApplicationName("Jarvis Desktop")
    from pathlib import Path
    launcher = Path(__file__).resolve().parents[1] / "Jarvis.exe"
    app.setWindowIcon(QIcon(str(Path(__file__).with_name("Jarvis.ico"))))
    backend = Ollama()
    try:
        window = Window(ChatService(backend), backend)
    except Exception as error:
        QMessageBox.critical(None, "Jarvis Desktop", str(error))
        return 1
    screen = app.screenAt(QCursor.pos()) or app.primaryScreen()
    if screen is not None:
        area = screen.availableGeometry()
        window.resize(min(window.width(), area.width()), min(window.height(), area.height()))
        frame = window.frameGeometry()
        frame.moveCenter(area.center())
        window.move(frame.topLeft())
    if sys.platform == "win32" and launcher.is_file():
        from .taskbar import set_taskbar_identity
        try:
            set_taskbar_identity(int(window.winId()), launcher)
        except OSError as error:
            window._set_status(f"Windows taskbar setup failed. {error}", True)
    window.show()
    return app.exec()

