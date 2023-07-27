# SmartVoiceAssistant
A smart voice assistant with multi-language support and long-term memory. Currently best for Swedish and English. Compatible with Windows and Raspberry Pi. The assistant can use various functions and tools to answer question (Google, Wolfram Alpha, etc.). Based on OpenAI's GPT-models, Google STT and TTS, and ElevenLabs TTS.

## Download
- Start by downloading all of the files in this repository as a ZIP-file, and unzip as a folder (with the files in it) on your device.

## Get API-keys, credentials and ID's
If you do not want to gather all of this information or do not have time, simply do not save them to the "apiKeys.py" file. Only the OpenAI API Key is required for the assistant to function. However, I recommend to use its full potential by filling in the information. It is really fascinating!
**Save these keys and ID's to the "apiKeys.py" file (only the OpenAI API Key is required):**
- [OpenAI API Key](https://platform.openai.com/account/api-keys): If you have an OpenAI account, you can find your API Key in the user settings.
- [Porcupine Access Key (Wake-word recognizer)](https://console.picovoice.ai/): Sign up for Picovoice Console to get your Access Key.
- [ElevenLabs API Key (Text-To-Speech)](https://elevenlabs.io/): Create an account, click the profile icon in the top-right corner, and get the API Key from "Profile Settings".
- [Wolfram Alpha App ID](https://developer.wolframalpha.com/): Sign up for a developer account, create an app under "My Apps" > "Get an AppID", and get the AppID
- Google
  - [Custom Search API Key (developerKey)](https://developers.google.com/custom-search/v1/overview): Create a new project and get the API Key by clicking "Get a Key".
  - [Search Engine ID (cx)](https://programmablesearchengine.google.com/controlpanel/all): Create a Search Engine (with whatever settings you like), then you can find its ID in "Overview" under the "Basic" section.
  - Cloud JSON Credentials File:
    1. Go to the [Google Cloud Console](https:/console.cloud.google.com/)
    1. Click on the Menu button, then go to "APIs & Services" > "Credentials"
    1. Select the service account you want to create a key for under "Service Accounts", or create a new one (click on "Create credentials" > "Service account")
    1. Click "Keys" > "Add Key" > "Create new key"
    1. Choose "JSON" as the key type and click on "Create"
    1. A JSON key file will be downloaded to your device
    1. Move the JSON file to the repository folder that all other files Python and JSON files are in

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
   ```python3 "{PROJECT DIRECTORY}\VoiceAssistant.py"```
   (Example: ```python "C:\Users\username\Documents\VoiceAssistant\test.py"```)

## Windows
### Set-Up
**Run these commands, and follow the steps to install the packages (PowerShell terminal):**
1. Open a PowerShell terminal as ADMIN
1. Install Python through [Windows Store](https://www.microsoft.com/store/productId/9NRWMJP3717K)
1. Install pip:
   ```Invoke-WebRequest -Uri https://bootstrap.pypa.io/get-pip.py -OutFile get-pip.py; python get-pip.py```
1. Create an environment:
   ```python -m venv "{PROJECT DIRECTORY}\venv"```
   (Example: ```python -m venv "C:\Users\username\Documents\VoiceAssistant\venv"```)
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
   (Example: ```& python "C:\Users\username\Documents\VoiceAssistant\test.py"```)
