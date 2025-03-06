import platform
import subprocess
import sys
import csv
import time

from PyQt6.QtGui import QStandardItem, QStandardItemModel, QBrush, QColor
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFrame,
    QPushButton,
    QTableView,
    QTextEdit,
    QFileDialog,
    QMessageBox, QHeaderView, QSplitter
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from host_adder import HostAddDialog, is_valid_ip  # Импортируем диалог из модуля

from icmplib import ping, exceptions


class PingThread(QThread):
    data_ready = pyqtSignal(str, dict)  # (hostname, {metrics})
    error_occurred = pyqtSignal(str, str)  # (hostname, error message)
    status_update = pyqtSignal(str)  # Новый сигнал для статуса

    def __init__(self, host):
        super().__init__()
        self.host = host
        self.running = True

    def stop(self):
        self.running = False

    def run(self):
        while self.running:  # Исправлено: runn ing → running
            try:
                result = ping(self.host, count=1, timeout=1, privileged=False)

                # Отправка статуса о успешном пинге
                rtt_ms = result.avg_rtt * 1000
                self.status_update.emit(f"Пинг {self.host} выполнен. RTT: {rtt_ms:.1f} ms")

                if result.is_alive:
                    rtt = int(rtt_ms)  # Исправлено: avg_rtt * 1000
                    loss_percent = round(result.packet_loss * 100, 2)  # Исправлено: 10 0 → 100
                    delivered = round((result.packets_received / result.packets_sent) * 100, 2)
                else:
                    rtt = None
                    loss_percent = '100%'
                    delivered = '0%'

                metrics = {
                    "rtt": rtt,
                    "delivered": delivered,  # Исправлено: deliv ered → delivered
                    "loss": loss_percent,
                    "last_ping": time.strftime("%Y-%m-%d %H:%M:%S")
                }

                self.data_ready.emit(self.host, metrics)  # Исправлено: e mit → emit

            except exceptions.ICMPTimeout:
                error_msg = f"Ошибка пинга {self.host}: Время ожидания ответа истекло"
                self.status_update.emit(error_msg)
                self.error_occurred.emit(self.host, "Время ожидания ответа истекло")

            except exceptions.NameLookupError:
                error_msg = f"Ошибка пинга {self.host}: Не удалось разрешить имя хоста"
                self.status_update.emit(error_msg)
                self.error_occurred.emit(self.host, "Не удалось разрешить имя хоста")

            except Exception as e:
                error_msg = f"Ошибка пинга {self.host}: {str(e)}"
                self.status_update.emit(error_msg)
                self.error_occurred.emit(self.host, str(e))

            time.sleep(1)


class TopFrame(QFrame):
    def __init__(self, table_model, status_text):
        super().__init__()
        self.table_model = table_model
        self.status_text = status_text
        self.init_ui()

    def init_ui(self):
        # Топ-фрейм оставлен пустым (можно добавить будущие элементы)
        layout = QHBoxLayout()
        self.setLayout(layout)
        self.setFixedHeight(50)


class FileActionsFrame(QFrame):
    def __init__(self, table_model: QStandardItemModel, status_text: QTextEdit):
        super().__init__()
        self.btn_import = None
        self.btn_export = None
        self.table_model = table_model
        self.status_text = status_text
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout()

        self.btn_export = QPushButton("Экспорт")
        self.btn_export.clicked.connect(self.export_to_csv)
        layout.addWidget(self.btn_export)

        self.btn_import = QPushButton("Импорт")
        self.btn_import.clicked.connect(self.import_from_csv)
        layout.addWidget(self.btn_import)

        layout.setAlignment(Qt.AlignmentFlag.AlignTop|Qt.AlignmentFlag.AlignHCenter)
        self.setLayout(layout)

# Перенесенные методы из TopFrame
    def export_to_csv(self):
        try:
            file_name, _ = QFileDialog.getSaveFileName(
                self,
                "Сохранить CSV",
                "",
                "CSV Files (*.csv);;All Files (*)"
            )
            if file_name:
                with open(file_name, 'w', encoding='utf-8-sig', newline='') as f:
                    writer = csv.writer(f, delimiter=';')
                    headers = [self.table_model.headerData(i, Qt.Orientation.Horizontal)
                               for i in range(self.table_model.columnCount())]
                    writer.writerow(headers)

                    for row in range(self.table_model.rowCount()):
                        row_data = []
                        for col in range(self.table_model.columnCount()):
                            item = self.table_model.item(row, col)
                            row_data.append(item.text() if item else "")
                        writer.writerow(row_data)
                self.status_text.append(f"Экспорт в {file_name} завершен")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def import_from_csv(self):
        try:
            file_name, _ = QFileDialog.getOpenFileName(
                self,
                "Выбрать CSV",
                "",
                "CSV Files (*.csv);;All Files (*)"
            )
            if file_name:
                with open(file_name, 'r', encoding='utf-8-sig') as f:
                    reader = csv.reader(f, delimiter=';')
                    next(reader)  # Пропуск заголовков
                    for row in reader:
                        if not row[0]:
                            continue

                        if is_valid_ip(row[0]):
                            self.table_model.appendRow([
                                QStandardItem(row[0]),
                                QStandardItem("0"),
                                QStandardItem("0"),
                                QStandardItem("0"),
                                QStandardItem("00:00:00")
                            ])
                        else:
                            self.status_text.append(f"Ошибка: {row[0]} — неверный формат IP")

                self.status_text.append(f"Импорт из {file_name} завершен")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))


class MiddleFrame(QFrame):
    def __init__(self, table_model: QStandardItemModel, status_text: QTextEdit):
        super().__init__()
        self.btn_monitor = None
        self.btn_add = None
        self.table_view = None
        self.table_model = table_model
        self.status_text = status_text
        self.ping_threads = []

        # Создаем экземпляр FileActionsFrame с передачей данных
        self.file_actions = FileActionsFrame(
            table_model=self.table_model,
            status_text=self.status_text
        )

        # Для хранения активных потоков
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout()
        # Создание рамки с тенью
        self.setFrameShape(QFrame.Shape.Box)  # Тип рамки: прямоугольная
        self.setFrameShadow(QFrame.Shadow.Raised)  # Тень: выпуклая

        # Настройка ширины рамки
        self.setLineWidth(1)

        # Создаем горизонтальный layout для кнопок
        buttons_layout = QVBoxLayout()
        buttons_layout.setAlignment(Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignTop)

        self.btn_add = QPushButton("Добавить хосты")
        self.btn_add.setFixedWidth(200)
        self.btn_add.clicked.connect(self.show_add_dialog)
        buttons_layout.addWidget(self.btn_add)

        self.btn_monitor = QPushButton("Наблюдение")
        self.btn_monitor.setFixedWidth(200)
        self.btn_monitor.clicked.connect(self.toggle_monitoring)
        buttons_layout.addWidget(self.btn_monitor)
        buttons_layout.addWidget(self.file_actions)

        # Таблица
        self.table_view = QTableView()

        # Настройка внешнего вида таблицы
        self.table_view.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive)  # Разрешаем изменение ширины столбцов
        self.table_view.verticalHeader().setVisible(False)  # Скрываем вертикальные заголовки
        self.table_view.horizontalHeader().setStretchLastSection(True)  # Растягиваем последний столбец
        self.table_view.horizontalHeader().setDefaultSectionSize(150)  # Устанавливаем начальную ширину столбцов
        self.table_view.setSortingEnabled(True)  # Включаем сортировку

        # Настройка выделения строк
        self.table_view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)  # Выделяем только целые строки
        self.table_view.setSelectionMode(QTableView.SelectionMode.SingleSelection)  # Разрешаем выделение одной строки

        # Отключение редактирования
        self.table_view.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)

        # Альтернативная окраска строк
        self.table_view.setAlternatingRowColors(True)

        self.table_view.setModel(self.table_model)
        layout.addWidget(self.table_view)
        layout.addLayout(buttons_layout)

        self.setLayout(layout)

    def toggle_monitoring(self):
        if self.btn_monitor.text() == "Наблюдение":
            # Запуск наблюдения
            # Проверка и исправление данных в таблице
            self.fix_table_columns()  # Новый метод для проверки

            self.start_monitoring()
        else:
            # Остановка наблюдения
            self.stop_monitoring()

    def fix_table_columns(self):
        """Исправление таблицы: добавление недостающих столбцов в строки"""
        required_columns = 5  # Количество столбцов в модели
        rows = self.table_model.rowCount()
        cols = self.table_model.columnCount()  # Общее количество столбцов модели

        # Убедимся, что модель имеет правильное количество столбцов
        if cols < required_columns:
            # Добавляем недостающие столбцы (если нужно)
            for _ in range(required_columns - cols):
                self.table_model.insertColumn(cols)
                cols += 1

        # Исправляем каждую строку
        for row in range(rows):
            for col in range(required_columns):
                if not self.table_model.item(row, col):
                    # Если элемент отсутствует — добавляем пустой
                    self.table_model.setItem(row, col, QStandardItem())

    def start_monitoring(self):
        # Очистка старых потоков
        self.stop_monitoring()

        # Запуск потоков для всех хостов
        self.ping_threads = []
        for row in range(self.table_model.rowCount()):
            host = self.table_model.item(row, 0).text()
            thread = PingThread(host)
            thread.data_ready.connect(self.update_metrics)
            thread.error_occurred.connect(self.handle_ping_error)
            thread.status_update.connect(self.update_status)

            thread.start()
            self.ping_threads.append(thread)

        self.btn_monitor.setText("Остановить наблюдение")

    def stop_monitoring(self):
        # Отправляем сигнал остановки
        for thread in self.ping_threads:
            thread.stop()

        # Ждем 0.5 секунд, чтобы потоки завершились
        for thread in self.ping_threads:
            if thread.isRunning():
                thread.quit()
                thread.wait(500)  # Таймаут 0.5 секунды

            # Принудительное завершение, если нужно
            if thread.isRunning():
                thread.terminate()

        self.ping_threads.clear()
        self.btn_monitor.setText("Наблюдение")

    def update_metrics(self, host, metrics):
        """Обновление таблицы с метриками и цветовой индикацией"""
        for row in range(self.table_model.rowCount()):
            current_host = self.table_model.item(row, 0).text()
            if current_host == host:
                # Определяем цвет в зависимости от статуса
                if metrics["rtt"] is not None:
                    # Успешный пинг
                    color = QColor("green")
                else:
                    # Проблемы с пингом
                    color = QColor("red")

                rtf = str(metrics["rtt"]) if metrics["rtt"] else "n/a"
                delivered_text = f"{metrics['delivered']}%" if metrics["rtt"] else "n/a"
                loss_text = f"{metrics['loss']}%" if metrics["rtt"] else "n/a"

                self.table_model.item(row, 1).setText(rtf)
                self.table_model.item(row, 1).setForeground(color)

                self.table_model.item(row, 2).setText(delivered_text)
                self.table_model.item(row, 2).setForeground(color)

                self.table_model.item(row, 3).setText(loss_text)
                self.table_model.item(row, 3).setForeground(color)

                self.table_model.item(row, 4).setText(metrics["last_ping"])
                self.table_model.item(row, 4).setForeground(color)

                break

    def handle_ping_error(self, host: str, error: str):
        self.status_text.append(f"Ошибка при пинге {host}: {error}")

    def show_add_dialog(self):
        dialog = HostAddDialog(self.table_model, self.status_text)
        if dialog.exec() == HostAddDialog.accepted:
            self.status_text.append("Диалог добавления закрыт успешно")

    def keyPressEvent(self, event):
        """Обработка нажатия клавиш."""
        if event.key() == Qt.Key.Key_Delete:
            self._delete_selected_record()
        else:
            super().keyPressEvent(event)

    def _delete_selected_record(self):
        selected_indexes = self.table_view.selectionModel().selectedRows()
        if not selected_indexes:
            return

        try:
            current_row = selected_indexes[0].row()
            host_text = self.table_model.item(current_row, 0).text()

            confirmation = QMessageBox.question(
                self,
                "Подтверждение удаления",
                f"Вы уверены, что хотите удалить хост: {host_text}",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if confirmation == QMessageBox.StandardButton.Yes:
                self.table_model.removeRow(current_row)
        except Exception as e:
            print(f"Ошибка при удалении записи: {e}")

    def update_status(self, message):
        self.status_text.append(f"[{time.strftime('%H:%M:%S')}] {message}")


class BottomFrame(QFrame):
    def __init__(self, status_text):
        super().__init__()
        self.status_text = status_text
        self.init_ui()

    def init_ui(self):
        # Создание рамки с тенью
        self.setFrameShape(QFrame.Shape.Box)  # Тип рамки: прямоугольная
        self.setFrameShadow(QFrame.Shadow.Raised)  # Тень: выпуклая

        # Настройка ширины рамки
        self.setLineWidth(1)

        layout = QHBoxLayout()
        layout.addWidget(self.status_text)
        self.setLayout(layout)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Network Monitor")
        self.setGeometry(100, 100, 800, 600)

        self.table_model = QStandardItemModel()
        self.table_model.setColumnCount(5)
        self.table_model.setHorizontalHeaderLabels([
            "Хост",
            "Ping, мс",
            "% доставленных",
            "% недоставленных",
            "Время последнего ping"
        ])

        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)

        main_layout = QVBoxLayout()
        self.top_frame = TopFrame(self.table_model, self.status_text)
        self.middle_frame = MiddleFrame(self.table_model, self.status_text)
        self.bottom_frame = BottomFrame(self.status_text)

        main_layout.addWidget(self.top_frame)

        splitter = QSplitter()
        splitter.setOrientation(Qt.Orientation.Vertical)

        splitter.addWidget(self.middle_frame)
        splitter.addWidget(self.bottom_frame)

        main_layout.addWidget(splitter)

        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
