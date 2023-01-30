import io
from time import sleep, time
import speech_recognition as sr
import whisper
import queue
import tempfile
import os
import threading
import click
import torch
import numpy as np
import warnings
import queue
import sqlite3
import datetime
import pwd
import wave
from dir_config import app_data_dir, db_dir, db, audio_dir, audio_temp_dir, error_log_dir
import logging
# Set up the logging configuration
logging.basicConfig(filename=error_log_dir + '/transcribe_error.log', level=logging.ERROR)

global running_recording 
running_recording = True

@click.command()
@click.option("--model", default="base", help="Model to use", type=click.Choice(["tiny","base", "small","medium","large"]))
@click.option("--english", default=True, help="Whether to use English model",is_flag=True, type=bool)
@click.option("--verbose", default=False, help="Whether to print verbose output", is_flag=True,type=bool)
@click.option("--energy", default=300, help="Energy level for mic to detect", type=int)
@click.option("--dynamic_energy", default=False,is_flag=True, help="Flag to enable dynamic engergy", type=bool)
@click.option("--pause", default=0.8, help="Pause time before entry ends", type=float)
@click.option("--save_entire_clip",default=True, help="Flag to save entire clip", is_flag=True,type=bool)
@click.option("--session_name", default="", help="Name of the session", type=str)
@click.option("--session_timestamp", default="", help="Timestamp of the session", type=str)
def main(model, english,verbose, energy, pause,dynamic_energy, save_entire_clip, session_name, session_timestamp):
    # Check timestamp format and make sure it is "%Y_%m_%d_%H_%M_%S"

    try:
        datetime.datetime.strptime(session_timestamp, '%Y_%m_%d_%H_%M_%S') 
    except ValueError:
        print("Incorrect data format, should be YYYY_MM_DD_HH_MM_SS")
        return

    os.makedirs(app_data_dir, exist_ok=True)
    if not os.path.exists(app_data_dir) or not os.access(app_data_dir, os.W_OK):
        raise(PermissionError("Set app_data_dir to another folder with access"))
    os.makedirs(db_dir, exist_ok=True)
    os.makedirs(audio_dir, exist_ok=True)
    os.makedirs(audio_temp_dir, exist_ok=True)

    # Create sqlite3 database called transcribe.db with 3 columns: date, timestamp
    conn = sqlite3.connect(db)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS transcribe (session_time text NOT NULL PRIMARY KEY UNIQUE, session_name text, session_text text)''')
    conn.commit()
    # Add timestamp to the following create table statement
    c.execute(f"CREATE TABLE IF NOT EXISTS {f'transcribe_session'} (timestamp INTEGER, session_time text, transcribed text)")
    c.execute("CREATE INDEX IF NOT EXISTS timestamp_idx ON transcribe_session (session_time)")
    conn.commit()
    print("session info created")
    #there are no english models for large
    if model != "large" and english:
        model = model + ".en"
    audio_model = whisper.load_model(model)
    audio_queue = queue.Queue()
    record_thread = threading.Thread(target=record_audio,
                    args=(audio_queue, energy, pause, dynamic_energy, session_timestamp))
    #record_thread.setDaemon(True)
    record_thread.start()
    # Add session entree to transcribe database
    c.execute(f"INSERT INTO transcribe VALUES ('{session_timestamp}', '{session_name}', 'NULL')")
    transcribe_thread = threading.Thread(target=transcribe_forever,
                    args=(audio_queue, audio_model, english, verbose, session_name, session_timestamp))
    #transcribe_thread.setDaemon(True)
    transcribe_thread.start()
    c.close()
    conn.close()
        

# specify parse transcribe database to list out the available sessions for the day
def list_session_of_the_day(year_month_date) -> list:
    conn = sqlite3.connect(db)
    c = conn.cursor()
    c.execute(f"SELECT * FROM transcribe WHERE date = '{year_month_date}'")
    result = c.fetchall()
    return result

def record_audio(audio_queue, energy, pause, dynamic_energy, session_timestamp):
    #load the speech recognizer and set the initial energy threshold and pause threshold

    r = sr.Recognizer()
    r.energy_threshold = energy
    r.pause_threshold = pause
    r.dynamic_energy_threshold = dynamic_energy
    with sr.Microphone(sample_rate=16000) as source:
        print("Recording...")
        i = 0
        while True:
            audio = r.listen(source)
            #get and save audio to wav file
            wav_file = wave.open(audio_temp_dir + '/audio_' + str(i) + '.wav', 'wb')
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(16000)
            wav_file.writeframes(audio.get_raw_data())
            wav_file.close()

            torch_audio = torch.from_numpy(np.frombuffer(audio.get_raw_data(), np.int16).flatten().astype(np.float32) / 32768.0)
            audio_data = torch_audio
            audio_queue.put_nowait(audio_data)
            i += 1


def transcribe_forever(audio_queue, audio_model, english, verbose, session_name, session_timestamp):
    # Create entry in transcribe database 

    # Create sqlite3 database to store a transcribe session with file name of timestamp of session
    
    try:
        conn = sqlite3.connect(db)
        c = conn.cursor()
        # Add timestamp to the following create table statement
        c.execute(f"""INSERT INTO transcribe_session VALUES ("{int(time())}", "{session_timestamp}", "Start of Transcription Session:")""")
        conn.commit()
        while True:
            current_timestamp = int(time())
            audio_data = audio_queue.get()
            result = audio_model.transcribe(audio_data,language='english')
            if not verbose:
                predicted_text = result["text"]
            else:
                predicted_text = result["text"]
            if predicted_text != " Thank you." and len(predicted_text) > 1:
                # generate current integer timestamp
                # Add entry to transcribe_session database with timestamp, date, session_times, predicted_text
                c.execute(f"""INSERT INTO transcribe_session VALUES ("{current_timestamp}", "{session_timestamp}", "{predicted_text}")""")
                conn.commit()
    except KeyboardInterrupt:
        conn.close()
        

main()
