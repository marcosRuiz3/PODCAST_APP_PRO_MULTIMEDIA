import sounddevice as sd
import soundfile as sf

# Cambia este nombre por uno de tus archivos reales
FILENAME = "grabaciones/rec_1765621946.wav"

data, sr = sf.read(FILENAME, always_2d=True)
print("Shape:", data.shape, "SR:", sr)
sd.play(data, sr)
sd.wait()
print("Terminado")
