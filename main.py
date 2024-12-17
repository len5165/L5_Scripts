import sys
import asyncio
import aiohttp
import sqlite3
from PyQt5.QtCore import QThread, pyqtSignal, QTimer
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QPushButton, QLabel, QListWidget, QProgressBar, \
    QWidget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Асинхронная загрузка данных")
        self.setGeometry(100, 100, 600, 400)

        self.layout = QVBoxLayout()
        self.load_button = QPushButton("Загрузить данные")
        self.load_button.clicked.connect(self.load_data)

        self.status_label = QLabel("Статус: Готов")
        self.progress_bar = QProgressBar()
        self.data_list = QListWidget()

        self.layout.addWidget(self.load_button)
        self.layout.addWidget(self.progress_bar)
        self.layout.addWidget(self.status_label)
        self.layout.addWidget(self.data_list)

        container = QWidget()
        container.setLayout(self.layout)
        self.setCentralWidget(container)

        self.timer = QTimer()
        self.timer.timeout.connect(self.check_updates)
        self.timer.start(10000)  # Проверять каждые 10 секунд

    def load_data(self):
        self.progress_bar.setValue(0)  # Сброс индикатора
        self.status_label.setText("Статус: Загрузка данных...")
        self.worker = DataLoader()
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.finished_signal.connect(self.on_data_loaded)
        self.worker.start()

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def on_data_loaded(self, data):
        self.status_label.setText("Статус: Сохранение данных...")
        self.saver = DataSaver(data)
        self.saver.finished_signal.connect(self.on_data_saved)
        self.saver.start()

    def on_data_saved(self):
        self.status_label.setText("Статус: Готов")
        self.load_data_from_db()

    def load_data_from_db(self):
        self.data_list.clear()
        conn = sqlite3.connect("data.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM posts")
        rows = cursor.fetchall()
        for row in rows:
            self.data_list.addItem(f"ID: {row[0]} - {row[1]}")
        conn.close()

    def check_updates(self):
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.status_label.setText("Статус: Загрузка в процессе, обновление отложено...")
        else:
            self.status_label.setText("Статус: Проверка обновлений...")
            self.worker = DataLoader()
            self.worker.progress_signal.connect(self.update_progress)
            self.worker.finished_signal.connect(self.on_data_loaded)
            self.worker.start()


class DataLoader(QThread):
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(list)

    async def fetch_data(self):
        url = "https://jsonplaceholder.typicode.com/posts"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                total_steps = 5
                for step in range(1, total_steps + 1):
                    await asyncio.sleep(0.5)  # Симуляция шагов загрузки
                    self.progress_signal.emit(int((step / total_steps) * 100))
                return await response.json()

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        data = loop.run_until_complete(self.fetch_data())
        self.finished_signal.emit(data)


class DataSaver(QThread):
    finished_signal = pyqtSignal()

    def __init__(self, data):
        super().__init__()
        self.data = data

    def run(self):
        conn = sqlite3.connect("data.db")
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY,
                title TEXT
            )
        """)
        conn.commit()
        for i, post in enumerate(self.data):
            cursor.execute("INSERT OR REPLACE INTO posts (id, title) VALUES (?, ?)", (post['id'], post['title']))
            conn.commit()
            self.msleep(100)  # Задержка для имитации длительного сохранения
        conn.close()
        self.finished_signal.emit()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
