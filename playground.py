import json
import os
import threading
import tkinter as tk

import pyperclip

import openai


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
    input_text.insert('end', "\n\nResponse " + output_text.get("1.0", 'end-1c'))

def on_copy_to_clipboard():
    pyperclip.copy(output_text.get("1.0", 'end-1c'))

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
                if not self.stopped and not self.stopped:
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
copy_button = tk.Button(user_input_frame, text="Copy to clipboard", command=on_copy_to_clipboard)
copy_button.pack(side = 'left')

# Create a checkbox to enable output_text to be prefixed with the content of input_text
echo_check = tk.BooleanVar()
echo_check_box = tk.Checkbutton(user_input_frame, text="Echo", variable=echo_check)
echo_check_box.pack(side = 'left')

# Create a Label for the output text
output_label = tk.Label

output_label = tk.Label(root, text="Completed text:")
output_label.pack()

# Create a Text widget for the output text
output_text = tk.Text(root, height=25, width=150)
output_text.pack()

# Bind shift-enter to submit button
root.bind('<Shift-Return>', on_submit)

# Run the Tkinter event loop
root.mainloop()
