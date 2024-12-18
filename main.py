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
        self.layout.addWidget(self.progress_bar)#Индикатор прогресса (progress_bar)
        self.layout.addWidget(self.status_label)
        self.layout.addWidget(self.data_list)

        container = QWidget()
        container.setLayout(self.layout)
        self.setCentralWidget(container)
        #Таймер (QTimer) настроен на проверку обновлений каждые 10 секунд
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_updates)
        self.timer.start(10000)  # Проверять каждые 10 секунд

    def load_data(self):
        self.progress_bar.setValue(0)  # Сброс индикатора
        self.status_label.setText("Статус: Загрузка данных...")
        self.worker = DataLoader()#Создает экземпляр DataLoader (рабочий поток) и подключает сигналы
        self.worker.progress_signal.connect(self.update_progress)#progress_signal — для обновления прогресса
        self.worker.finished_signal.connect(self.on_data_loaded)#finished_signal — для обработки завершения загрузки
        self.worker.start()

    def update_progress(self, value):#Обновляет индикатор прогресса
        self.progress_bar.setValue(value)

    def on_data_loaded(self, data):
        self.status_label.setText("Статус: Сохранение данных...")
        self.saver = DataSaver(data)#Создает экземпляр DataLoader (рабочий поток) и подключает сигналы
        self.saver.finished_signal.connect(self.on_data_saved)#finished_signal — для обработки завершения загрузки
        self.saver.start()#После загрузки данных запускает процесс сохранения в базу данных

    def on_data_saved(self):#После сохранения данных обновляет интерфейс, загружая данные из базы
        self.status_label.setText("Статус: Готов")
        self.load_data_from_db()

    def load_data_from_db(self):#Загружает данные из базы данных и отображает их в списке
        self.data_list.clear()
        conn = sqlite3.connect("data.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM posts")
        rows = cursor.fetchall()
        for row in rows:
            self.data_list.addItem(f"ID: {row[0]} - {row[1]}")
        conn.close()

    def check_updates(self):
        #Проверяет наличие обновлений (например, новых данных).
        #Если загрузка уже выполняется, откладывает проверку.
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.status_label.setText("Статус: Загрузка в процессе, обновление отложено...")
        else:
            self.status_label.setText("Статус: Проверка обновлений...")
            self.worker = DataLoader()
            self.worker.progress_signal.connect(self.update_progress)
            self.worker.finished_signal.connect(self.on_data_loaded)
            self.worker.start()


#Класс DataLoader наследуется от QThread, что позволяет выполнять задачи в фоновом потоке,
# чтобы не блокировать основной поток (например, графический интерфейс).
class DataLoader(QThread):#отвечает за асинхронную загрузку данных с удаленного сервера
    progress_signal = pyqtSignal(int) #progress_signal: Этот сигнал используется для передачи прогресса выполнения задачи (в процентах). Он принимает целое число (int)
    finished_signal = pyqtSignal(list)#Этот сигнал используется для уведомления о завершении загрузки данных.
                                        #Он передает список (list), содержащий загруженные данные.

    async def fetch_data(self): #этот метод выполняет асинхронную загрузку данных с удаленного сервера
        url = "https://jsonplaceholder.typicode.com/posts"#Указывается URL, с которого будут загружаться данные
        async with aiohttp.ClientSession() as session:#Создается асинхронная сессия с помощью aiohttp.ClientSession()
            async with session.get(url) as response:#Выполняется GET-запрос к указанному URL Результат запроса сохраняется в переменной response
                total_steps = 5 #Для имитации прогресса загрузки используется цикл с 5 шагами
                for step in range(1, total_steps + 1):
                    await asyncio.sleep(0.5)  # На каждом шаге выполняется задержка в 0.5 секунды с помощью await asyncio.sleep(0.5)
                    self.progress_signal.emit(int((step / total_steps) * 100))
                    #Прогресс вычисляется как (step / total_steps) * 100 и передается через сигнал progress_signal
                return await response.json()
                #После завершения имитации прогресса данные извлекаются из ответа с помощью метода response.json().
                #Метод response.json() возвращает данные в формате JSON (список словарей)

    def run(self):#Этот метод выполняется в фоновом потоке и содержит основную логику загрузки данных
        loop = asyncio.new_event_loop()#Создается новый цикл событий asyncio с помощью asyncio.new_event_loop()
        asyncio.set_event_loop(loop)#Устанавливается текущий цикл событий с помощью asyncio.set_event_loop(loop)
        data = loop.run_until_complete(self.fetch_data())#Асинхронная функция fetch_data() выполняется с помощью loop.run_until_complete()
                                                        #Этот метод блокирует выполнение до завершения функции fetch_data()
        self.finished_signal.emit(data)
        #После завершения загрузки данных отправляется сигнал finished_signal, который передает загруженные данные

class DataSaver(QThread):#позволяет выполнять сохранение данных в фоновом потоке, чтобы не блокировать основной поток (например, графический интерфейс)
    finished_signal = pyqtSignal()#это сигнал, который используется для уведомления основного потока о завершении сохранения данных

    def __init__(self, data):
        super().__init__()
        self.data = data#Переменная self.data хранит данные, которые будут сохранены в базе данных

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
            self.msleep(100)  # Задержка для имитации длительного сохранения 100миллисекунд
        conn.close()
        self.finished_signal.emit()#Сигнал finished_signal отправляется, чтобы уведомить основной поток о завершении работы


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
