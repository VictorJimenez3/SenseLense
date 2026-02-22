try:
    import pyaudio
except ImportError:
    pyaudio = None
import wave

def record_wav(path, seconds=10, sample_rate=16000, channels=1, chunk_size=1024):
    """
    Records audio from the default input device and saves it to a WAV file.
    """
    if pyaudio is None:
        print("[!] PyAudio is not installed or no audio device found. Skipping recording.")
        return

    p = pyaudio.PyAudio()
    
    try:
        stream = p.open(format=pyaudio.paInt16,
                        channels=channels,
                        rate=sample_rate,
                        input=True,
                        frames_per_buffer=chunk_size)

        print(f"[*] Recording for {seconds} seconds...")
        frames = []

        for _ in range(0, int(sample_rate / chunk_size * seconds)):
            data = stream.read(chunk_size, exception_on_overflow=False)
            frames.append(data)

        print("[*] Recording complete.")

        stream.stop_stream()
        stream.close()
        
        with wave.open(path, 'wb') as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
            wf.setframerate(sample_rate)
            wf.writeframes(b''.join(frames))
            
    finally:
        p.terminate()
