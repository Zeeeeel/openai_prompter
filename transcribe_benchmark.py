import time
import whisper
import torch

model = whisper.load_model("medium")
# measure the time it takes to transcribe
time_start = time.time()
import datetime
a = datetime.datetime.now()

result = model.transcribe("/Users/ziyeliu/Code/play_ground/audio_recording/consolidated_audio.wav")
b = datetime.datetime.now()
print(result["text"])
delta = b - a
print(delta)