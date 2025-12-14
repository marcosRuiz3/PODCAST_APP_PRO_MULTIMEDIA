from PySide6.QtCore import Signal, Qt
from pyqtgraph import PlotWidget, mkPen, InfiniteLine
import soundfile as sf
import numpy as np

class WaveformWidget(PlotWidget):
    positionChanged = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.plotItem.showGrid(x=True, y=True)
        self.setBackground('#2b2b2b') # Fondo oscuro para que quede chulo
        self._curve = None
        self._line = None
        self._duration = 0.0

        # Buffers para tiempo real
        self._realtime_data = np.zeros(200) # Guardamos los últimos 200 puntos
        self._ptr = 0

        # Configuración ratón
        self.setMouseEnabled(x=False, y=False)
        self._dragging = False

    def plot_file(self, filename, downsample=10):
        """Modo estático: Pinta el archivo completo"""
        # Habilitar eje inferior normal
        self.getPlotItem().setLabel('bottom', text='Tiempo (s)')
        
        data, sr = sf.read(filename, always_2d=True)
        mono = data.mean(axis=1)
        if downsample > 1:
            mono = mono[::downsample]
            sr = sr / downsample
        x = np.linspace(0, len(mono) / sr, num=len(mono))
        self._duration = float(len(mono) / sr)

        self.clear()
        self._curve = self.plot(x, mono, pen=mkPen('#00bcd4', width=1)) # Cian
        
        self._line = InfiniteLine(pos=0.0, angle=90, movable=False, pen=mkPen('r', width=1))
        self.addItem(self._line)

    def start_recording_mode(self):
        """Prepara la gráfica para recibir datos en vivo"""
        self.clear()
        self._realtime_data = np.zeros(200) 
        # Creamos una curva que actualizaremos constantemente
        self._curve = self.plot(self._realtime_data, pen=mkPen('#d9534f', width=2)) # Rojo para grabar
        self.setYRange(-1, 1) # La amplitud de audio va de -1 a 1
        self.getPlotItem().hideAxis('bottom') # Ocultamos tiempo exacto porque es rolling

    def update_realtime(self, amplitude):
        """Añade un nuevo punto de amplitud y desplaza la gráfica"""
        # Desplazamos los datos hacia la izquierda (efecto scroll)
        self._realtime_data[:-1] = self._realtime_data[1:]
        # Ponemos el nuevo dato al final (usamos valor negativo y positivo para simular onda)
        self._realtime_data[-1] = amplitude 
        
        # Truco visual: pintamos simétrico para que parezca audio
        # (Esto es opcional, pero queda mejor ver la onda arriba y abajo)
        # Para simplificar, pintamos solo amplitud positiva en este ejemplo simple
        self._curve.setData(self._realtime_data)

    def set_cursor(self, seconds):
        if self._line is None: return
        if seconds < 0: seconds = 0
        if self._duration > 0 and seconds > self._duration: seconds = self._duration
        self._line.setPos(seconds)

    def _mouse_pos_to_time(self, event):
        vb = self.getViewBox()
        mouse_point = vb.mapSceneToView(event.position())
        x = mouse_point.x()
        if x < 0: x = 0
        if self._duration > 0 and x > self._duration: x = self._duration
        return float(x)

    def mousePressEvent(self, event):
        if self._line is not None and event.button() == Qt.LeftButton:
            self._dragging = True
            t = self._mouse_pos_to_time(event)
            self.set_cursor(t)
            self.positionChanged.emit(t)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._dragging and self._line is not None:
            t = self._mouse_pos_to_time(event)
            self.set_cursor(t)
            self.positionChanged.emit(t)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._dragging:
            self._dragging = False
            event.accept()
            return
        super().mouseReleaseEvent(event)