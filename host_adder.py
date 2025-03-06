from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QTextEdit,
    QDialogButtonBox,
    QMessageBox
)
from PyQt6.QtGui import QStandardItem


class HostAddDialog(QDialog):
    def __init__(self, table_model, status_text):
        super().__init__()
        self.host_input = None
        self.table_model = table_model
        self.status_text = status_text
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        self.host_input = QTextEdit()
        self.host_input.setPlaceholderText("Вставьте хосты (каждый с новой строки)")
        layout.addWidget(self.host_input)

        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        btn_box.accepted.connect(self.add_hosts)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

        self.setLayout(layout)

    def add_hosts(self):
        text = self.host_input.toPlainText()
        hosts = [line.strip() for line in text.split('\n') if line.strip()]

        valid_hosts = []
        for host in hosts:
            if is_valid_ip(host):
                valid_hosts.append(host)
            else:
                self.status_text.append(f"Ошибка: {host} — неверный формат IP")

        added_hosts = []
        for host in valid_hosts:
            # Проверка на существование хоста в таблице
            exists = False
            for row in range(self.table_model.rowCount()):
                item = self.table_model.item(row, 0)
                if item and item.text() == host:
                    exists = True
                    break
            if not exists:
                added_hosts.append(host)
                new_row = [
                    host,
                    "0",
                    "0%",
                    "0%",
                    "00:00:00"
                ]
                self.table_model.appendRow([QStandardItem(item) for item in new_row])
            else:
                self.status_text.append(f"Предупреждение: {host} уже существует в списке")

        if added_hosts:
            self.status_text.append(f"Добавлено {len(added_hosts)} хостов")
            self.host_input.clear()
            self.accept()
        else:
            QMessageBox.warning(
                self,
                "Ошибка",
                "Нет валидных хостов для добавления или все хосты уже существуют"
            )


def is_valid_ip(ip):
    parts = ip.split('.')
    if len(parts) != 4:
        return False
    for part in parts:
        if not part.isdigit():
            return False
        num = int(part)
        if not (0 <= num <= 255):
            return False
    return True
