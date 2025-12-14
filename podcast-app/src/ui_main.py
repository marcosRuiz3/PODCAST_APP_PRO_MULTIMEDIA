import sys, time, os, sqlite3
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QMessageBox,
)
from PySide6.QtCore import QTimer, Qt
from recorder import Recorder
from player import Player
from db import init_db, add_recording, list_recordings, update_recording_meta, DB_PATH
from waveform_widget import WaveformWidget
import soundfile as sf 

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Podcast App Pro") # ¡Nuevo nombre!
        self.rec = None
        self.player = Player()
        self.current_filename = None
        self.loaded_filename = None 
        self.record_start_time = None # Para contar segundos al grabar
        
        init_db()

        # Widgets
        self.btn_rec = QPushButton("Grabar")
        self.btn_stop = QPushButton("Parar")
        self.btn_play = QPushButton("Reproducir")
        self.btn_pause = QPushButton("Pausar")
        self.btn_delete = QPushButton("Eliminar")
        self.btn_export = QPushButton("Exportar a FLAC")
        self.lst = QListWidget()
        self.wave = WaveformWidget()
        self.title_edit = QLineEdit()
        self.desc_edit = QTextEdit()
        self.btn_save_meta = QPushButton("Guardar cambios")
        self.lbl_duration = QLabel("Duración / Tiempo: 0.0 s") # Etiqueta multiuso

        # Estilos
        self.btn_rec.setStyleSheet("QPushButton { background-color: #d9534f; color: white; } QPushButton:disabled { background-color: #f2b7b4; color: #aaaaaa; }")
        self.btn_play.setStyleSheet("QPushButton { background-color: #5cb85c; color: white; } QPushButton:disabled { background-color: #b9e2b9; color: #aaaaaa; }")
        self.btn_pause.setStyleSheet("QPushButton { background-color: #f0ad4e; color: white; } QPushButton:disabled { background-color: #f8d9a8; color: #aaaaaa; }")
        self.btn_export.setStyleSheet("QPushButton { background-color: #5bc0de; color: white; } QPushButton:disabled { background-color: #add8e6; color: #aaaaaa; }")

        # Layouts
        left_layout = QVBoxLayout()
        left_layout.addWidget(self.btn_rec)
        left_layout.addWidget(self.btn_stop)
        left_layout.addWidget(self.btn_play)
        left_layout.addWidget(self.btn_pause)
        left_layout.addWidget(self.btn_delete)
        left_layout.addWidget(self.btn_export)
        left_layout.addWidget(QLabel("Lista de grabaciones:"))
        left_layout.addWidget(self.lst)

        right_layout = QVBoxLayout()
        right_layout.addWidget(QLabel("Detalles de la grabación"))
        right_layout.addWidget(QLabel("Título:"))
        right_layout.addWidget(self.title_edit)
        right_layout.addWidget(QLabel("Descripción:"))
        right_layout.addWidget(self.desc_edit)
        right_layout.addWidget(self.btn_save_meta)
        right_layout.addWidget(self.lbl_duration)
        right_layout.addWidget(QLabel("Visualización:"))
        right_layout.addWidget(self.wave)

        main_layout = QHBoxLayout()
        main_layout.addLayout(left_layout, 1)
        main_layout.addLayout(right_layout, 2)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Listo")

        # Conexiones
        self.btn_rec.clicked.connect(self.start_record)
        self.btn_stop.clicked.connect(self.stop_record_or_playback)
        self.btn_play.clicked.connect(self.play_selected)
        self.btn_pause.clicked.connect(self.pause_playback)
        self.btn_delete.clicked.connect(self.delete_selected)
        self.btn_export.clicked.connect(self.export_compressed)
        self.btn_save_meta.clicked.connect(self.save_meta)
        self.lst.itemSelectionChanged.connect(self.on_selection_changed)
        self.wave.positionChanged.connect(self.on_wave_position_changed)

        # Timer (ahora más rápido para animaciones suaves: 50ms)
        self.timer = QTimer()
        self.timer.setInterval(50) 
        self.timer.timeout.connect(self.update_ui_timer)
        self.timer.start()

        # Estado inicial
        self.btn_stop.setEnabled(False)
        self.btn_play.setEnabled(False)
        self.btn_pause.setEnabled(False)
        self.btn_delete.setEnabled(False)
        self.btn_export.setEnabled(False)

        self.load_list()

    # ---------- Grabación ----------

    def start_record(self):
        os.makedirs("grabaciones", exist_ok=True)
        filename = f"rec_{int(time.time())}.wav"
        filepath = os.path.join("grabaciones", filename)

        self.rec = Recorder(filepath)
        self.rec.start()
        self.record_start_time = time.time() # Guardamos la hora de inicio
        self.current_filename = filepath
        self.status_bar.showMessage(f"GRABANDO EN VIVO... {filepath}")
        
        # Configurar la gráfica en modo grabación
        self.wave.start_recording_mode()

        self.btn_rec.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.btn_play.setEnabled(False)
        self.btn_pause.setEnabled(False)
        self.btn_delete.setEnabled(False)
        self.title_edit.setEnabled(False)
        self.desc_edit.setEnabled(False)
        self.btn_save_meta.setEnabled(False)
        self.lst.setEnabled(False)

    def stop_record(self):
        if self.rec:
            self.rec.stop()
            info = sf.info(self.rec.filename)
            duration = info.frames / info.samplerate
            add_recording(self.rec.filename, title=self.rec.filename, description="", duration=duration)
            self.status_bar.showMessage(f"Grabación finalizada: {self.rec.filename}")
            self.rec = None
            self.record_start_time = None
            
            self.btn_rec.setEnabled(True)
            self.btn_stop.setEnabled(False)
            self.title_edit.setEnabled(True)
            self.desc_edit.setEnabled(True)
            self.btn_save_meta.setEnabled(True)
            self.lst.setEnabled(True)
            self.load_list()
            if self.lst.count() > 0:
                self.lst.setCurrentRow(0)

    # ---------- Reproducción ----------

    def play_selected(self):
        items = self.lst.selectedItems()
        if not items: return
        filename = items[0].data(Qt.UserRole)
        title_text = items[0].text()
        
        if not filename or not os.path.exists(filename):
            self.status_bar.showMessage("Error: Archivo no encontrado")
            return

        if self.loaded_filename != filename:
            self.player.load(filename)
            self.loaded_filename = filename
            start_sec = 0.0
        else:
            start_sec = self.player.pos / self.player.sr if self.player.sr else 0.0

        self.player.play(start_sec=start_sec)
        
        dur = len(self.player.data) / self.player.sr if self.player.sr else 0
        self.lbl_duration.setText(f"Duración Total: {round(dur, 2)} s")
        self.status_bar.showMessage(f"Reproduciendo: {title_text}")

        self.btn_rec.setEnabled(False)
        self.btn_play.setEnabled(False)
        self.btn_pause.setEnabled(True)
        self.btn_stop.setEnabled(True)
        self.btn_delete.setEnabled(False)
        self.lst.setEnabled(False)

    def pause_playback(self):
        if self.player.data is None: return
        if self.player.is_playing:
            self.player.pause()
            self.btn_rec.setEnabled(True)
            self.btn_play.setEnabled(True)
            self.btn_pause.setEnabled(True)
            self.btn_stop.setEnabled(True)
            self.status_bar.showMessage("Pausado")
        else:
            start_sec = self.player.pos / self.player.sr if self.player.sr else 0.0
            self.player.play(start_sec=start_sec)
            self.btn_rec.setEnabled(False)
            self.btn_play.setEnabled(False)
            self.btn_pause.setEnabled(True)
            self.btn_stop.setEnabled(True)
            self.status_bar.showMessage("Reproduciendo")

    def stop_playback(self):
        if self.player.data is None: return
        self.player.stop()
        self.btn_rec.setEnabled(True)
        self.btn_play.setEnabled(True if self.current_filename else False)
        self.btn_pause.setEnabled(False)
        self.btn_stop.setEnabled(False)
        self.btn_delete.setEnabled(True if self.current_filename else False)
        self.lst.setEnabled(True)
        self.status_bar.showMessage("Listo")
        self.wave.set_cursor(0)

    def stop_record_or_playback(self):
        if self.rec is not None:
            self.stop_record()
        else:
            self.stop_playback()

    def on_wave_position_changed(self, seconds: float):
        if self.player.data is None: return
        if self.player.sr:
            self.player.pos = int(seconds * self.player.sr)
        if self.player.is_playing:
            self.player.pause()
            self.player.play(start_sec=seconds)
            self.status_bar.showMessage(f"Seek: {round(seconds, 2)} s")
        else:
            self.wave.set_cursor(seconds)
            self.status_bar.showMessage(f"Posición: {round(seconds, 2)} s")

    # ---------- Timer Centralizado (UI Loop) ----------
    
    def update_ui_timer(self):
        # CASO 1: ESTAMOS GRABANDO
        if self.rec is not None:
            # A. Actualizar tiempo
            elapsed = time.time() - self.record_start_time
            # Formato MM:SS
            mins, secs = divmod(int(elapsed), 60)
            self.lbl_duration.setText(f"GRABANDO: {mins:02d}:{secs:02d}")
            
            # B. Actualizar onda en tiempo real
            amp = self.rec.current_amplitude
            self.wave.update_realtime(amp)
            return

        # CASO 2: ESTAMOS REPRODUCIENDO
        if self.player.data is not None and self.player.is_playing:
            if self.player.sr == 0 or self.player._start_time is None: return
            
            total_sec = len(self.player.data) / self.player.sr
            elapsed = time.time() - self.player._start_time
            seconds = min(elapsed, total_sec)
            
            self.wave.set_cursor(seconds)
            # Actualizamos también el label de tiempo mientras reproduce
            self.lbl_duration.setText(f"Reproduciendo: {round(seconds, 1)} / {round(total_sec, 1)} s")

            if seconds >= total_sec:
                self.player.stop()
                self.wave.set_cursor(total_sec)
                self.stop_playback()

    # ---------- Gestión ----------

    def delete_selected(self):
        items = self.lst.selectedItems()
        if not items: return
        filename = items[0].data(Qt.UserRole)
        title_text = items[0].text()

        reply = QMessageBox.question(self, "Eliminar", f"¿Eliminar '{title_text}'?", QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes: return

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("DELETE FROM recordings WHERE filename=?", (filename,))
        conn.commit()
        conn.close()

        if os.path.exists(filename):
            os.remove(filename)

        if self.loaded_filename == filename:
            self.player.stop()
            self.loaded_filename = None

        self.status_bar.showMessage(f"Eliminado: {title_text}")
        self.current_filename = None
        self.load_list()
        self.btn_play.setEnabled(False)
        self.btn_pause.setEnabled(False)
        self.btn_delete.setEnabled(False)
        self.btn_stop.setEnabled(False)
        self.lst.setEnabled(True)
        self.title_edit.clear()
        self.desc_edit.clear()
        self.lbl_duration.setText("Duración: 0.0 s")
        self.wave.clear()

    def on_selection_changed(self):
        items = self.lst.selectedItems()
        if not items:
            self.current_filename = None
            self.btn_play.setEnabled(False)
            self.btn_delete.setEnabled(False)
            self.btn_pause.setEnabled(False)
            self.btn_export.setEnabled(False)
            self.title_edit.clear()
            self.desc_edit.clear()
            self.lbl_duration.setText("Duración: 0.0 s")
            return

        filename = items[0].data(Qt.UserRole)
        self.current_filename = filename

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT title, description, duration FROM recordings WHERE filename=?", (filename,))
        row = c.fetchone()
        conn.close()

        if row:
            title, desc, dur = row
            self.title_edit.setText(title if title else filename)
            self.desc_edit.setPlainText(desc)
            self.lbl_duration.setText(f"Duración: {round(dur if dur else 0, 2)} s")
        
        if os.path.exists(filename):
            self.wave.plot_file(filename)
            if self.rec is None:
                self.btn_play.setEnabled(True)
                self.btn_delete.setEnabled(True)
                self.btn_export.setEnabled(True)
                self.btn_pause.setEnabled(False)
                self.btn_stop.setEnabled(False)

    def save_meta(self):
        if not self.current_filename: return
        title = self.title_edit.text()
        desc = self.desc_edit.toPlainText()
        update_recording_meta(self.current_filename, title, desc)
        self.status_bar.showMessage("Metadatos guardados")
        self.load_list() 

    def load_list(self):
        self.lst.clear()
        rows = list_recordings()
        for r in rows:
            _id, title, filename, desc, created_at, duration = r
            text = title if title else filename
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, filename) 
            self.lst.addItem(item)
            if self.current_filename == filename:
                self.lst.setCurrentItem(item)

    def export_compressed(self):
        if not self.current_filename or not os.path.exists(self.current_filename): return
        out_filename = self.current_filename.replace(".wav", ".flac")
        try:
            self.status_bar.showMessage("Comprimiendo audio (FLAC)...")
            QApplication.processEvents()
            data, sr = sf.read(self.current_filename)
            sf.write(out_filename, data, sr)
            size_wav = os.path.getsize(self.current_filename)
            size_flac = os.path.getsize(out_filename)
            reduction = (1 - (size_flac / size_wav)) * 100
            msg = f"Exportado: {os.path.basename(out_filename)}\nAhorro: {reduction:.1f}%"
            QMessageBox.information(self, "Exportación FLAC", msg)
            self.status_bar.showMessage(f"Guardado: {os.path.basename(out_filename)}")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

def run():
    app = QApplication(sys.argv)
    w = MainWindow()
    w.resize(1000, 600)
    w.show()
    sys.exit(app.exec())