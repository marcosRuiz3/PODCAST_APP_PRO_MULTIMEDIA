import sounddevice as sd
import soundfile as sf
import queue
import threading
import numpy as np  # Necesitamos numpy para calcular el volumen

class Recorder:
    def __init__(self, filename, samplerate=44100, channels=1):
        self.filename = filename
        self.samplerate = samplerate
        self.channels = channels
        self._q = queue.Queue()
        self._recording = False
        self._thread = None
        # Variable para almacenar el volumen actual (0.0 a 1.0)
        self.current_amplitude = 0.0

    def _callback(self, indata, frames, time_info, status):
        if status:
            print("Recorder status:", status)
        
        # 1. Guardamos datos para el archivo
        self._q.put(indata.copy())
        
        # 2. Calculamos la amplitud máxima del fragmento actual (volumen)
        # Esto es lo que leerá la interfaz gráfica
        if len(indata) > 0:
            self.current_amplitude = np.max(np.abs(indata))

    def start(self):
        if self._recording:
            return
        self._recording = True
        self.current_amplitude = 0.0
        self._thread = threading.Thread(target=self._record_thread, daemon=True)
        self._thread.start()

    def _record_thread(self):
        with sf.SoundFile(self.filename, mode='w', samplerate=self.samplerate, channels=self.channels) as f:
            with sd.InputStream(samplerate=self.samplerate, channels=self.channels, callback=self._callback):
                while self._recording:
                    try:
                        data = self._q.get(timeout=0.1)
                    except queue.Empty:
                        continue
                    f.write(data)

    def stop(self):
        if not self._recording:
            return
        self._recording = False
        self._thread.join()