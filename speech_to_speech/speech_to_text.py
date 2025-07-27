import os
import pyaudio
import wave
from google.cloud import speech

# Setup environment
os.environ["GOOGLE_CLOUD_PROJECT"] = "ace-well-467010-f5"
os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"ace-well-467010-f5-7cf97226dec2.json"

# ====== Record Audio ======
def record_audio(filename="live_audio.wav", duration=7):
    chunk = 1024  # Record in chunks
    sample_format = pyaudio.paInt16
    channels = 1
    fs = 16000  # Sample rate
    p = pyaudio.PyAudio()

    print("Recording...")
    stream = p.open(format=sample_format, channels=channels, rate=fs,
                    frames_per_buffer=chunk, input=True)
    frames = []

    for _ in range(0, int(fs / chunk * duration)):
        data = stream.read(chunk)
        frames.append(data)

    stream.stop_stream()
    stream.close()
    p.terminate()

    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(p.get_sample_size(sample_format))
        wf.setframerate(fs)
        wf.writeframes(b''.join(frames))

    print(f"Audio saved as {filename}")


# ====== Convert Speech to Text using Google Cloud ======
def speech_to_text(filename="live_audio.wav"):
    client = speech.SpeechClient()

    with open(filename, "rb") as audio_file:
        content = audio_file.read()

    audio = speech.RecognitionAudio(content=content)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=16000,
        language_code="en-US"
    )

    response = client.recognize(config=config, audio=audio)

    for result in response.results:
        print("Transcript:", result.alternatives[0].transcript)


if __name__ == "__main__":
    record_audio(duration=5)
    speech_to_text()
