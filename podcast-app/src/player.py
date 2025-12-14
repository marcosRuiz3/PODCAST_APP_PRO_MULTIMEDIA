import sounddevice as sd
import soundfile as sf
import time

class Player:
    def __init__(self):
        self.data = None      # numpy array (frames x channels)
        self.sr = 0           # samplerate
        self.pos = 0          # posición actual estimada (frames)
        self.is_playing = False
        self._start_time = None  # instante de inicio en time.time()

    def load(self, filename):
        sd.stop()
        self.is_playing = False
        self._start_time = None
        data, sr = sf.read(filename, always_2d=True)
        self.data = data
        self.sr = sr
        self.pos = 0

    def play(self, start_sec=0.0):
        if self.data is None or self.sr == 0:
            return
            
        # 1. Calcular posición en frames
        self.pos = int(start_sec * self.sr)
        
        # 2. Protección: si estamos al final, no reproducir o ir al inicio
        if self.pos >= len(self.data):
            self.pos = 0
            start_sec = 0.0

        # 3. Guardar referencia de tiempo para calcular cursor visual
        self._start_time = time.time() - start_sec
        self.is_playing = True

        sd.stop()
        
        # CORRECCIÓN 2: Slicing del array. 
        # Reproducimos SOLO desde self.pos hasta el final.
        # Si no hacemos [self.pos:], siempre reproduce desde el segundo 0.
        sd.play(self.data[self.pos:], self.sr)

    def pause(self):
        if not self.is_playing:
            return
        sd.stop()
        self.is_playing = False
        if self._start_time is not None:
            # Calcular dónde nos hemos quedado realmente
            elapsed = time.time() - self._start_time
            self.pos = int(elapsed * self.sr)

    def stop(self):
        if self.data is None:
            return
        sd.stop()
        self.is_playing = False
        self.pos = 0
        self._start_time = None