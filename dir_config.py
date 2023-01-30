import os
import tempfile

# Get the temporary directory
temp_dir = tempfile.gettempdir()

app_data_dir = os.path.join(os.path.expanduser("~"), 'Downloads', "OAIToolKit")
db_dir = os.path.join(app_data_dir, "database")
db = os.path.join(db_dir, "transcribe.db")
audio_dir = os.path.join(app_data_dir, "audio_recording")
audio_temp_dir = os.path.join(app_data_dir, "audio_recording_temp")
error_log_dir = temp_dir
