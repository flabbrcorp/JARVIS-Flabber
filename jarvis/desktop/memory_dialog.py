"""Review, add, correct, and forget memories from Jarvis Desktop."""
import sqlite3

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QLabel,
    QLineEdit, QListWidget, QPlainTextEdit, QPushButton, QVBoxLayout,
)


class MemoryDialog(QDialog):
    def __init__(self, memory, chat_id, parent):
        super().__init__(parent)
        self.memory, self.chat_id = memory, chat_id
        self.setWindowTitle("Jarvis Memory")
        self.resize(600, 560)
        self.setStyleSheet("QDialog { background: #191a20; } QLineEdit { background: #22232c; padding: 6px; }")
        layout = QVBoxLayout(self)
        actions = QHBoxLayout()
        self.add = QPushButton("+ Add memory")
        self.add.clicked.connect(self.new_memory)
        actions.addWidget(self.add)
        actions.addStretch()
        layout.addLayout(actions)
        self.items = QListWidget()
        self.items.currentRowChanged.connect(self.select)
        layout.addWidget(self.items, 1)

        form = QFormLayout()
        self.title = QLineEdit()
        self.title.setMaxLength(80)
        self.content = QPlainTextEdit()
        self.content.setFixedHeight(80)
        self.scope = QComboBox()
        self.scope.addItem("When relevant", "relevant")
        self.scope.addItem("Every chat", "standing")
        form.addRow("Title", self.title)
        form.addRow("Memory", self.content)
        form.addRow("Use", self.scope)
        layout.addLayout(form)
        self.info = QLabel()
        self.info.setWordWrap(True)
        self.info.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.info)
        controls = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        controls.rejected.connect(self.reject)
        self.save_button = controls.addButton("Save memory", QDialogButtonBox.ButtonRole.ActionRole)
        self.save_button.clicked.connect(self.save)
        self.forget_button = controls.addButton("Forget memory", QDialogButtonBox.ButtonRole.ActionRole)
        self.forget_button.clicked.connect(self.confirm_forget)
        layout.addWidget(controls)
        self.reload()

    def reload(self, selected=None):
        self.records = self.memory.list()
        self.items.blockSignals(True)
        self.items.clear()
        selected_row = -1
        for index, record in enumerate(self.records):
            self.items.addItem(record["title"])
            if record["id"] == selected:
                selected_row = index
        self.items.setCurrentRow(selected_row)
        self.items.blockSignals(False)
        self.select(selected_row)

    def new_memory(self):
        self.items.setCurrentRow(-1)
        self.select(-1)
        self.title.setFocus()

    def select(self, index):
        record = self.records[index] if index >= 0 else None
        self.memory_id = record["id"] if record else None
        self.forget_button.setEnabled(record is not None)
        self.forget_button.setText("Forget memory")
        self.title.setText(record["title"] if record else "")
        self.content.setPlainText(record["content"] if record else "")
        self.scope.setCurrentIndex(self.scope.findData(record["scope"] if record else "relevant"))
        self.info.setText(
            f"Saved from {record['source_title'] or 'Jarvis Desktop'} · Revision {record['revision']}"
            if record else "Add a short preference, project fact, or instruction."
        )

    def save(self):
        try:
            self.memory.save(self.title.text(), self.content.toPlainText(),
                             self.scope.currentData(), self.chat_id, self.memory_id)
        except (ValueError, sqlite3.Error) as error:
            self.info.setText(str(error))
            return
        self.reload(self.memory_id)
        self.info.setText("Memory saved.")

    def confirm_forget(self):
        if self.memory_id is None:
            return
        if self.forget_button.text() != "Confirm forget":
            self.forget_button.setText("Confirm forget")
            self.info.setText("This removes the saved memory and its revisions. Chat messages stay in history.")
            return
        try:
            self.memory.forget(self.memory_id)
        except sqlite3.Error as error:
            self.info.setText(str(error))
            return
        self.reload()
        self.info.setText("Memory forgotten.")

