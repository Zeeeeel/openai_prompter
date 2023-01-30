import json
import os
import threading
import tkinter as tk
from tkinter import messagebox, simpledialog
from pydub import AudioSegment
import pyperclip
import sqlite3
import openai
import subprocess
import atexit
import queue
import sys
from time import sleep


# import transcribe

def on_closing():
    root.destroy()
    transcribe_action.transcribe_stop()

def on_submit(event=None):

    global streaming_thread

    # Get the input text from the user
    prompt = input_text.get("1.0", 'end-1c')
    
    # Clear the input text
    output_text.delete("1.0", tk.END)
    
    # Create and start a new thread to stream the completions
    streaming_thread = StreamingThread(prompt,  selected_template = template.get(), echo_check = echo_check.get())
    streaming_thread.start()

def on_stop():
    global streaming_thread
    streaming_thread.stop()
    
def on_copy_to_input():
    output_text.clipboard_clear()
    output_text.clipboard_append(output_text.get("1.0", 'end-1c'))
    # print Response: if output does not contain it as a substring
    if "Response:" not in output_text.get("1.0", 'end-1c'):
        input_text.insert('end', "\n\nResponse: " + output_text.get("1.0", 'end-1c'))

def on_copy_input_to_clipboard():
    pyperclip.copy(input_text.get("1.0", 'end-1c'))

def on_copy_output_to_clipboard():
    pyperclip.copy(output_text.get("1.0", 'end-1c'))

class TranscribeAction:
    def __init__(self):
        self.transcribe_Thread = None
        self.transcribe_started = False

    def transcribe_start(self):
        self.transcribe_started = False
        # Clear the input and outtext
        input_text.delete("1.0", tk.END)
        output_text.delete("1.0", tk.END)

        # Ask for confirmation
        result = messagebox.askokcancel("Transcribe Session", "Do you want to start a transcribe session?")
        if result == True:
            # Get the name of the transcribe session
            session_name = simpledialog.askstring("Transcribe Session", "Please enter the name of the transcribe session:")
            # Create and start a new thread to stream the completions
            self.transcribe_Thread = TranscribeThread(session_name)
            self.transcribe_Thread.start()
        self.transcribe_started = True

    def transcribe_stop(self):
        if self.transcribe_started:
            self.transcribe_Thread.stop()
                # Directory where the .wav files are located
            directory = os.path.abspath('/Users/ziyeliu/Code/play_ground/audio_recording_temp/')

            # Initialize an empty audio file
            consolidated_audio = AudioSegment.empty()

            # Iterate through all .wav files in the directory
            for filename in os.listdir(directory):
                if filename.endswith('.wav'):
                    # Load the audio file
                    audio = AudioSegment.from_file(os.path.join(directory, filename))
                    # Append the audio file to the consolidated audio
                    consolidated_audio += audio

            # Export the consolidated audio to a new file
            consolidated_audio.export("audio_recording/consolidated_audio.wav", format="wav")
            # Delete delete temp folder
            os.system("rm -r audio_recording_temp")
            
transcribe_action = TranscribeAction()

class TranscribeThread(threading.Thread):
    def __init__(self, session_name):
        super().__init__()
        self.stopped = False
        self.output_queue = queue.Queue() 
        # remove all instance of '`' in session_name
        session_name = session_name.replace('`', '')
        # print current  timestamp in string forma
        from datetime import datetime
        self.session_name = session_name
        self.timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
        self.transcribe_process = None

    
    def run(self):
        self.transcribe_process = subprocess.Popen([sys.executable, '/Users/ziyeliu/Code/play_ground/transcribe.py', '--model', 'small', '--pause', '0.6', '--session_name', self.session_name, '--session_timestamp', self.timestamp], stderr=subprocess.PIPE) 

        atexit.register(self.stop)

        # Get the output from the other program
        last_checked_timestamp = 0
        conn = sqlite3.connect(os.path.abspath('/Users/ziyeliu/Code/play_ground/database/transcribe.db')) 
        while True:
            # Check for new changes
            try:
                cursor = conn.execute(f"SELECT timestamp, session_time, transcribed FROM transcribe_session WHERE session_time = '{self.timestamp}' and timestamp > {last_checked_timestamp}")
            except sqlite3.OperationalError:
                #print("Waiting for first transcript")
                sleep(0.1)
                continue
            rows = cursor.fetchall()
            if len(rows)>0:
                # get the last timestamp from all the rows
                rows.sort(key=lambda x: x[0])
                if len(rows) > 0:
                    for row in rows:
                        row = list(row)
                        # Check to see if the last 3 characters are '...' and if so, remove them
                        if row[2][-3:] == '...':
                            row[2] = row[2][:-3]
                            output_text.insert('end', "- " + row[2])
                        # print the text
                        print(row[2])
                        # add the text to the output queue
                        output_text.insert('end', "- " + row[2] + '\n')
                last_checked_timestamp = rows[-1][0]
            sleep(0.1)

    def stop(self):
        # stop if run() no longer executing
        self.stopped = True
        # terminate the process if it is still running
        if self.transcribe_process and self.transcribe_process.poll() is None:
            self.transcribe_process.terminate()
        print("Transcribe session stopped")

class StreamingThread(threading.Thread):
    def __init__(self, prompt, selected_template, echo_check):
        super().__init__()
        self.selected_template = selected_template
        template = data[self.selected_template]
        self.prompt = template+prompt
        if self.selected_template == 'Chat' and input_text.get("1.0", tk.END)[0:len(data[self.selected_template])] != data[self.selected_template]:    
            self.prompt = self.prompt + "\nAI: "
            input_text.delete("1.0", tk.END)
            input_text.insert("1.0", self.prompt)
        self.stopped = False
        self.echo_check = echo_check
    
    def run(self):
        try:
            # Call the OpenAI API to start streaming completions
            print(self.prompt)
            completions = openai.Completion.create(
                engine="text-davinci-003",
                prompt= self.prompt,
                max_tokens=2000,
                n=1,
                stop=None,
                temperature=0,
                stream=True,
            )
            if self.echo_check:
                output_text.insert("end", self.prompt)
            for completion in completions:
                if not self.stopped:
                    # Insert the completed text into the output text widget
                    output_text.insert('end', completion['choices'][0]['text'])
                    output_text.see('end')
                else:
                    break
        except Exception as e:
                output_text.delete("1.0", tk.END)
                output_text.insert('end', e)
                output_text.see('end')
        if self.selected_template == 'Chat':    
            input_text.insert('end', output_text.get("1.0", 'end-1c')+ "\nHuman: ")

    def stop(self):
        self.stopped = True

# Set the API key=
openai.api_key = os.environ.get('OpenAIToken') 

# Create a new Tkinter window
root = tk.Tk()
root.title("OpenAI Text Completion")

# Create a Label for the template selection
template_label = tk.Label(root, text="Select template:")
template_label.pack()

# Load the JSON file
with open("/Users/ziyeliu/Code/play_ground/template.json", "r") as read_file:
    data = json.load(read_file)

# Get all the options from the JSON file
options = [option for option in data]

# Set the default option
template = tk.StringVar(root)
template.set(options[0])

template_frame = tk.Frame(root)
template_frame.pack()

# Create the toggle switch
for option in options:
    template_button = tk.Radiobutton(template_frame, text=option, variable=template, value=option)
    template_button.pack(side = 'left')

# Create a Label for the input text
input_label = tk.Label(root, text="Enter text to complete:")
input_label.pack()

# Create a Text widget for the input text
input_text = tk.Text(root, height=25, width=150)
input_text.pack()

user_input_frame = tk.Frame(root)
user_input_frame.pack()

# Create a Button to submit the input text
submit_button = tk.Button(user_input_frame, text="Submit", command=on_submit)
submit_button.pack(side = 'left')

# Create a Button to stop the streaming
stop_button = tk.Button(user_input_frame, text="Stop", command=on_stop)
stop_button.pack(side = 'left')

# Create a Button to copy the output text to the input text
copy_button = tk.Button(user_input_frame, text="Copy to input field", command=on_copy_to_input)
copy_button.pack(side = 'left')

# Create a Button to copy the output text to clipboard
copy_button = tk.Button(user_input_frame, text="Copy to input to clipboard", command=on_copy_input_to_clipboard)
copy_button.pack(side = 'left')

# Create a checkbox to enable output_text to be prefixed with the content of input_text
echo_check = tk.BooleanVar()
echo_check_box = tk.Checkbutton(user_input_frame, text="Echo", variable=echo_check)
echo_check_box.pack(side = 'left')

# Create transcribe frame
transcribe_frame = tk.Frame(root)
transcribe_frame.pack()

# Create a Button to start transcribe
transcribe_start_button = tk.Button(transcribe_frame, text="Start transcribe", command=transcribe_action.transcribe_start)
transcribe_start_button.pack(side = 'left')

# Create a Button to stop transcribe
transcribe_stop_button = tk.Button(transcribe_frame, text="Stop transcribe", command=transcribe_action.transcribe_stop)
transcribe_stop_button.pack(side = 'left')

# Create a Label for the output text
output_label = tk.Label

output_label = tk.Label(root, text="Completed text:")
output_label.pack()

# Create a Text widget for the output text
output_text = tk.Text(root, height=25, width=150)
output_text.pack()

# Create output frame
user_output_frame = tk.Frame(root)
user_output_frame.pack()

# Create a Button to copy the output text to clipboard
copy_button = tk.Button(user_output_frame, text="Copy to output to clipboard", command=on_copy_output_to_clipboard)
copy_button.pack(side = 'left')

# Bind shift-enter to submit button
root.bind('<Shift-Return>', on_submit)
root.protocol("WM_DELETE_WINDOW", on_closing)
# Run the Tkinter event loop
root.mainloop()
