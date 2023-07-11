# SmartVoiceAssistant
A smart voice assistant with multi-language support and long-term memory. Currently best for Swedish and English. Compatible with Windows and Raspberry Pi. The assistant can use various functions and tools to answer question (Google, Wolfram Alpha, etc.). Based on OpenAI's GPT-models, Google STT and TTS, and ElevenLabs TTS.

## Raspberry Pi
### Set-Up
**Run these commands to install packages on a Raspberry Pi (terminal):**
- ```sudo apt-get install flac espeak sox portaudio19-dev```
- ```sudo pip3 install pyaudio pvporcupine pyttsx3 SpeechRecognition requests openai google-api-python-client python-vlc Adafruit_DHT luma.led_matrix wolframalpha langchain google-cloud-speech google-cloud-texttospeech mutagen tiktoken colorama```

### Run the program
1. Open the terminal
1. Run python script:
   ```python {PROJECT DIRECTORY}\VoiceAssistant.py```
   **OR** run python3 script:
   ```& python3 "{PROJECT DIRECTORY}\VoiceAssistant.py"```
1. Example:
```& python "C:\Users\username\Documents\VoiceAssistant\test.py"```

## Windows
### Set-Up
**Run these commands, and follow the steps to install the packages (PowerShell terminal):**
1. Open a PowerShell terminal as ADMIN
1. Install Python through [Windows Store](https://www.microsoft.com/store/productId/9NRWMJP3717K)
1. Install pip:
   ```Invoke-WebRequest -Uri https://bootstrap.pypa.io/get-pip.py -OutFile get-pip.py; python get-pip.py```
1. Create an environment:
   ```python -m venv "{PROJECT DIRECTORY}\venv"```
   Example:
   ```python -m venv "C:\Users\username\Documents\VoiceAssistant\venv"```
1. Activate the environment:
   ```& "{PROJECT DIRECTORY}\venv\Scripts\Activate.ps1"```
1. Install packages:
   ```pip install pyaudio pvporcupine pyttsx3 SpeechRecognition requests openai google-api-python-client pygame wolframalpha langchain google-cloud-speech google-cloud-texttospeech mutagen tiktoken colorama```

### Run the program
**Run these commands to start the program in Windows PowerShell:**
1. Open a PowerShell terminal as ADMIN
1. Let PowerShell execute scripts in Windows:
   ```Set-ExecutionPolicy -ExecutionPolicy RemoteSigned```
1. Activate the environment (If it isn't already activated after installation):
   ```& "{PROJECT DIRECTORY}\venv\Scripts\Activate.ps1"```
1. Run python script:
   ```& python "{PROJECT DIRECTORY}\VoiceAssistant.py"```
   **OR** run python3 script:
   ```& python3 "{PROJECT DIRECTORY}\VoiceAssistant.py"```
   Example:
   ```& python "C:\Users\username\Documents\VoiceAssistant\test.py"```
