from google.cloud import texttospeech
import os

# Setup environment
os.environ["GOOGLE_CLOUD_PROJECT"] = "ace-well-467010-f5"
os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"ace-well-467010-f5-7cf97226dec2.json"

# Initialize the client
client = texttospeech.TextToSpeechClient()

# Text input
text = "You are a zone safety classifier agent for a public event. You will be given descriptions of 4 different zones based on video analysis. Each description contains an estimate of crowd density, movement quality, and estimated number of people."

synthesis_input = texttospeech.SynthesisInput(text=text)

# Select voice
voice = texttospeech.VoiceSelectionParams(
    language_code="en-US",
    ssml_gender=texttospeech.SsmlVoiceGender.FEMALE
)

# Select audio file format
audio_config = texttospeech.AudioConfig(
    audio_encoding=texttospeech.AudioEncoding.MP3
)

# Perform the TTS request
response = client.synthesize_speech(
    input=synthesis_input,
    voice=voice,
    audio_config=audio_config
)

# Save to file
with open("output.mp3", "wb") as out:
    out.write(response.audio_content)

print("Audio content written to output.mp3")


# os.startfile("output.mp3")

import pygame
pygame.mixer.init()
pygame.mixer.music.load("output.mp3")
pygame.mixer.music.play()
while pygame.mixer.music.get_busy():
    continue
