import os, time, math, re, json, pyttsx3, requests, pvporcupine, struct, pyaudio, datetime, tiktoken
import speech_recognition as sr
from colorama import init, Fore, Back, Style
from urllib.request import urlopen
from googleapiclient.discovery import build
from langchain.utilities.wolfram_alpha import WolframAlphaAPIWrapper
from google.cloud import texttospeech

try:
    # For Raspberry Pi
    import Adafruit_DHT
    from luma.led_matrix.device import max7219
    from luma.core.interface.serial import spi, noop
    from luma.core.render import canvas
    MAX7219Lib = True
except:
    print("No MAX7219 or Adafruit packages found, using settings to not use 8x8 matrix display")
    MAX7219Lib = False

try:
    import vlc # For Raspberry Pi
    print("VLC package found (this is best for Raspberry Pi's)")
    vlcLib = True
except:
    print("No VLC package found (this is fine if you have Pygame installed)")
    vlcLib = False
try:
    import pygame # For Windows
    pygameLib = True
    print("Pygame package found (this is best for Windows)")
except:
    print("No Pygame package found (this is fine if you have VLC installed)")
    pygameLib = False

try:
    from google.cloud import speech
except:
    print("No Google Cloud package found (offline STT will be used instead)")
    googleSTT = False

from CustomSettings import assistantSpeechOn, offlineTTS, textInput, keepOnListening, listenTime, sumHistoryTime, messageLimit, startPrompt, summarizePrompt
from CustomSettings import wakeUpWords, STABILITY, SIMILARITY_BOOST, VOICE_ID, animationFPS, googleSTT, swedish, english, maxToolsPerPrompt, openAIdelay
from CustomSettings import googleTTS_name, googleTTS_gender, swedishStartPrompt, wakeWordOn, wakeSpeaker, speakerSleepTime, RaspberryPi, devMode, overrideMemPrompt
from CustomSettings import sweOverrideMemPrompt, GPT4, elevenLabs, wolframAlpha, googleSearch
from apiKeys import openai_api_key, porcupineAccessKey, XI_API_KEY, googleCustomSearchAPI, googleSearchEngineID, GOOGLE_JSON_CREDENTIALS, wolframAlphaAppID
import openai
openai.api_key = openai_api_key

init(autoreset=True) # Initializes Colorama (print colored text)

if wolframAlpha:
    os.environ["WOLFRAM_ALPHA_APPID"] = wolframAlphaAppID
    wolfram = WolframAlphaAPIWrapper()

if RaspberryPi:
    try:
        from ctypes import *
        ERROR_HANDLER_FUNC = CFUNCTYPE(None, c_char_p, c_int, c_char_p, c_int, c_char_p) # Define our error handler type
        def py_error_handler(filename, line, function, err, fmt):
            pass
        c_error_handler = ERROR_HANDLER_FUNC(py_error_handler)
        asound = cdll.LoadLibrary('libasound.so')
        asound.snd_lib_error_set_handler(c_error_handler) # Set error handler
        print("Libasound module found (Libasound error handling will be used)")
    except:
        print("No Libasound module found (No Libasound error handling will be used)")
        RaspberryPi = False

# Porcupine (Wake-word recognizer)
if wakeWordOn:
    try:
        porcupine = pvporcupine.create(
            access_key=porcupineAccessKey,
            keywords=wakeUpWords # Wake-up-words
        )
    except:
        print("No Porcupine Access Key found in apiKeys.py file (wake-word recognizer will not be used)")
        wakeWordOn = False

scriptDir = os.path.dirname(os.path.abspath(__file__))
longTermMemoryPath = os.path.join(scriptDir, "longTermMemory.json")
textToSpeechFilePath = os.path.join(scriptDir, "textToSpeech.mp3")
googleCredentialPath = os.path.join(scriptDir, GOOGLE_JSON_CREDENTIALS)

#googleCredentialsExists = True

if os.path.exists(googleCredentialPath):
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = googleCredentialPath
else:
    #googleCredentialsExists = False
    print(Style.BRIGHT+Fore.RED+"WARNING: Google JSON Credentials File was not found. Please provide a valid file name for it in apiKeys.py to use Google STT and TTS.")
    if swedish:
        print(Style.BRIGHT+Fore.RED+"Assistant requires Google STT and TTS to talk Swedish, which means that only english is used until you have fixed this.")
        swedish = False
        english = True
    googleSTT = False
    print("Using another STT in english instead")

# ElevenLabs
OUTPUT_PATH = "textToSpeech.mp3"

# IP info, location
IPinfoURL='http://ipinfo.io/json'
IPinfoResponse=urlopen(IPinfoURL)
IPinfoData=json.load(IPinfoResponse)
city = IPinfoData['city']
postal = IPinfoData['postal']
timezone = IPinfoData['timezone']
country = IPinfoData['country']
if country == "SE": country = "Sweden"

if MAX7219Lib == True:
    
    from mutagen.mp3 import MP3

    from images import loading_frames, talk_frames, think_frame

    # Define pins for MAX7219
    serial = spi(port=0, device=0, gpio=noop())
    device = max7219(serial, cascaded=1)

    # Define pin for DHT11
    dht11_pin = 4

    sensor = Adafruit_DHT.DHT11

    animationSPF = 1/animationFPS

# Offline text-to-speech
tts = pyttsx3.init()
tts.startLoop(False)

# PyAudio
pa = None
audio_stream = None

# Speech-to-text
stt = sr.Recognizer()

# Initialize pygame
if (pygameLib == True) and (vlcLib == False):
    pygame.init()
    pygame.mixer.init()

frameLength = 512
sampleRate = 16000

hasSummarized = True

lastOpenAIresponse = time.time() - openAIdelay
start_time = time.time()
lastSoundTime = 0

history = []
messages = []
messageCount = 0
totAnswerTokens = 0

messageTokens = 0
kwargs = {}
totalCost = 0

rstMemStage = 0
saveMemStage = 0
memRstChoice = ''

math_functions = {
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    "exp": math.exp,
    "log": math.log,
    "log10": math.log10,
    "sqrt": math.sqrt,
    "ceil": math.ceil,
    "floor": math.floor,
    "pi": math.pi,
    "e": math.e
}

# Infinite main loop
def main():

    # Listen for wake-word
    if wakeWordOn:
        pcm = audio_stream.read(porcupine.frame_length)
        pcm = struct.unpack_from("h" * porcupine.frame_length, pcm)
        keyword_index = porcupine.process(pcm)

    if (wakeWordOn == False) or (textInput == True): keyword_index = 1 # Trigger a virtual "wake-word detected", to go into the loop instantly

    global start_time
    global hasSummarized
    global lastSoundTime

    if keyword_index >= 0: # If wake-word detected
        if wakeWordOn and (textInput == False): print(Style.NORMAL+Fore.WHITE+"Wake-word detected")
        if MAX7219Lib == True: animate(loading_frames, animationSPF) # Visualize assistant wake-up on matrix display
        start_time = time.time()
        while time.time() - start_time < listenTime: # Listen for certain amount of seconds
            if textInput == True:
                userPrompt = input(Style.BRIGHT + Fore.GREEN + 'User: '+ Style.NORMAL)
            else:
                if googleSTT == True:
                    userPrompt = googleSpeechToText()
                else:
                    userPrompt = speechToText() # Listen to speech from user
                closeAudioStream() # Stop listening (to not trigger speech when assistant is talking)
            if userPrompt is not None or userPrompt != '':
                if textInput == False: print(Style.BRIGHT+Fore.GREEN+"User: "+Style.NORMAL+userPrompt)
            if userPrompt == None or userPrompt == '': # If there was no speech
                break # Break out of loop, and restart
            else: # If there was speech
                if MAX7219Lib == True: still(think_frame, 0) # Visualize thinking on matrix display
                
                toolAnswer = useTool(userPrompt)
                answer(userPrompt, toolAnswer)

                if wakeSpeaker and assistantSpeechOn: lastSoundTime = time.time()
                hasSummarized = False
                start_time = time.time()
                if keepOnListening == False: break # Stop listening, if keepOnListening is set to false by user
                else: openAudioStream() # Start listning again
        # Restart
        if MAX7219Lib == True: animate(reversed(loading_frames), animationSPF) # Visualize assistant sleep on matrix display
        openAudioStream()
        if wakeWordOn and (textInput == False): print(Style.NORMAL+Fore.WHITE+"Waiting for wake-word")
        elif (wakeWordOn == False) and (textInput == False): print("Listening...")

    if time.time() - start_time > sumHistoryTime: # if (time.time() - start_time > sumHistoryTime) and (hasSummarized == False) # TEST
        print(Fore.YELLOW+str(sumHistoryTime)+" seconds has passed since last conversation")
        summarizeHistory()
        if wakeWordOn and (textInput == False): print("Waiting for wake-word")
        elif (wakeWordOn == False) and (textInput == False): print("Listening...")

    if wakeSpeaker and assistantSpeechOn and (time.time() - lastSoundTime > speakerSleepTime):
        beep()
        lastSoundTime = time.time()

def youSure(memory, sureBool=True):
    global overrideMemPrompt
    global sweOverrideMemPrompt

    if english == True:
        
        if 'SAVE' in memory: # Ask to save memory
            toolAnswer = '[PRIO]You must ask the user, in your next message, for approval if you understood correctly that the short term memory (current conversation) of this device is preferred to be saved to the long term memory.'
            
        else: # Ask to delete memory
            if 'BOTH' in memory: text="BOTH the long term memory AND short term memory of this device are"
            elif 'LONG TERM' in memory: text="the long term memory of this device is"
            elif 'SHORT TERM' in memory: text="the short term memory of this device is"
            if sureBool == False:
                toolAnswer = "[PRIO]"+overrideMemPrompt+f"You must ask the user again, in your next message, for approval if you understood correctly that {text} preferred to be deleted. Ask if the user meant to say yes or no."
            else:
                toolAnswer = "[PRIO]"+overrideMemPrompt+f'You must ask the user, in your next message, for approval if you understood correctly that {text} preferred to be deleted. Ask if the user meant to say yes or no.'

    elif english == False:

        if 'SAVE' in memory: # Ask to save memory
            toolAnswer = '[PRIO]Du har en falsk konversation med en användare. Låtsas att du kan spara minne på den här enheten. Du MÅSTE be användaren, i ditt nästa meddelande, om godkännande om du förstått rätt att korttidsminnet (aktuell konversation) för denna enhet föredras att sparas i långtidsminnet.'
            
        else: # Ask to delete memory
            if 'BOTH' in memory: text="BÅDE långtidsminnet OCH korttidsminnet för denna enhet"
            elif 'LONG TERM' in memory: text="den här enhetens långtidsminne"
            elif 'SHORT TERM' in memory: text="korttidsminnet för denna enhet"
            if sureBool == False:
                toolAnswer = "[PRIO]"+sweOverrideMemPrompt+f"Du måste be användaren igen, i ditt nästa meddelande, om godkännande om du förstått rätt att {text} föredras att bli raderat. Be användaren att svara ja eller nej."
            else:
                toolAnswer = "[PRIO]"+sweOverrideMemPrompt+f'Du måste be användaren, i ditt nästa meddelande, om godkännande om du förstått rätt att {text} föredras att bli raderat. Be användaren att svara ja eller nej.'


    return toolAnswer

def userApprove(userPrompt):
    approveMsgs = [{"role": "user", "content": userPrompt}]
    approveFuncList = [
                {
                    "name": "yes_or_no",
                    "description": 'Determine if the user said “yes” or “no” in any way (in Swedish or English). You must be certain, otherwise choose "UNSURE".',
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "decision": {
                                "type": "string",
                                "enum": ["YES", "NO","UNSURE"]
                            },
                        },
                        "required": ["decision"]
                    }
                }
            ]
    approveResponse=generateResponse(approveMsgs, approveFuncList, 0.2, {"name": "yes_or_no"})

    if approveResponse.get("function_call"): # Check if it wanted to use a function
        functionArgs = json.loads(approveResponse["function_call"]["arguments"])
        approveDecision = functionArgs.get("decision")
    else:
        approveDecision = 'UNSURE'
    return approveDecision
    
def useTool(userPrompt):

    global maxToolsPerPrompt, devMode, wolframAlpha, googleSearch
    useTools = True
    stringToolAnswers = ''
    toolsUsedNum = 0
    toolAnswers = []
    toolMsgs = []
    appendPrevSummations(toolMsgs)
    toolMsgs.extend(history)
    toolMsgs.append({'role':'user','content':userPrompt})
    
    toolStartPrompt = (
            "You can use the following tools to answer the user's latest message:\n"
            +('{WOLFRAM ALPHA} Provides answers to mathematics, science, technology, society and culture, and weather (location-based).\n' if wolframAlpha else "")
            +('{GOOGLE SEARCH} Can search for anything. Best used for up-to-date information.\n' if googleSearch else "")
            +("{TEMP SENSOR} Gives current room temperature.\n" if MAX7219Lib else "")
            +'{SIMPLE CALCULATOR} Answers simple calculations.\n'
            +'{LOCATION} Provides current device location.\n'
            +'{TIME & DATE} Access the current date and time.\n'
            +"{SAVE MEMORY} ONLY if the user CLEARLY conveyed to want to save, remember or summarize current conversation to the device's long-term-memory.\n" # +"{SAVE MEMORY} ONLY if the user CLEARLY conveyed to want to save or summarize current conversation to the device's long-term-memory.\n"
            +"{RESET MEMORY} If the user wants to reset/delete/clear the device's memory/database/messages, or are deciding on what memory to reset/delete.\n\n"
            +"To use a tool, write {} with its name in braces. If you can answer without a tool, write {YES}.\n\n"
            +'Examples:\n'
            +('Weather info: {LOCATION}, {WOLFRAM ALPHA}\n' if wolframAlpha else "")
            +'Greeting user: {YES}\n'
            +("Obama's age to the power of 2: {TIME & DATE}, {WOLFRAM ALPHA}\n" if wolframAlpha else "")
            +("Pewdiepie's height subtracted by Marzia's height: {GOOGLE SEARCH}, {SIMPLE CALCULATOR}\n" if googleSearch else "")
            +("Holidays today: {TIME & DATE}, {GOOGLE SEARCH}\n" if googleSearch else "")
            +"Memory deletion or clear database: {RESET MEMORY}\n"
            +"Recall or remember info from long-term memory: {YES}\n"
            +'Unsure/unnecessary: {YES}\n\n'
            +'Choose a tool now within {}, nothing else.'
            )
    
    toolMsgs.append({'role':'system','content':toolStartPrompt})
    response1=generateResponse(toolMsgs, temp=0.2, max_tokens=8) # Choose a tool

    if devMode: print("response1:",response1)

    # Extract the text in braces
    match1 = re.search(r'\{(.+?)\}', response1)
    if match1: response1 = match1.group(1)
    toolMsgs.append({'role':'assistant','content':'{'+response1+'}'})

    while useTools:
        
        if 'SAVE MEMORY' in response1:

            print(Fore.YELLOW+"Assistant used memory save tool:")

            global saveMemStage

            if saveMemStage == 1: # Did the user approve?
                decision=userApprove(userPrompt)
                if decision == 'YES':
                    print(Fore.YELLOW+"User accepted: Short-term memory will be saved shortly")
                    summarizeOutput = summarizeHistory(userPrompt)
                    toolAnswer = f'[PRIO]'+summarizeOutput
                    saveMemStage = 0
                elif decision == 'NO':
                    print(Fore.YELLOW+"User canceled: Short-term memory will not be saved")
                    toolAnswer = ''
                    saveMemStage = 0
                else: # UNSURE
                    toolAnswer=youSure('SAVE')
                    print(Fore.YELLOW+"Checking if the target is correct again...")

            elif saveMemStage == 0: # Ask if the user is sure
                print(Fore.YELLOW+"Target: save short-term memory")
                toolAnswer=youSure('SAVE')
                print(Fore.YELLOW+"Checking if the target is correct...")
                saveMemStage = 1

            toolAnswers.append(toolAnswer)
            break # Use no more tools

        else:
            saveMemStage = 0

        if 'RESET MEMORY' in response1:

            print(Fore.YELLOW+"Assistant used memory reset tool:")

            global rstMemStage
            global memRstChoice
            global overrideMemPrompt
            global sweOverrideMemPrompt

            if rstMemStage == 2: # Did the user approve?
                decision=userApprove(userPrompt)
                if decision == 'YES':
                    print(Fore.YELLOW+"User accepted deletion: Memory will be removed shortly")

                    if english == True:
                        if 'LONG TERM' in memRstChoice:
                            text = 'long'
                            mem = text
                        elif 'SHORT TERM' in memRstChoice:
                            text = 'short'
                            mem = text
                        elif 'BOTH' in memRstChoice:
                            text = 'both long term and short'
                            mem = 'both'
                        toolAnswer = f'[PRIO][{mem}]{overrideMemPrompt}You MUST inform the user in you next message that you are deleting {text} term memory from this device'
                    elif english == False:
                        if 'LONG TERM' in memRstChoice:
                            text = 'lång'
                            mem = 'long'
                        elif 'SHORT TERM' in memRstChoice:
                            text = 'kort'
                            mem = 'short'
                        elif 'BOTH' in memRstChoice:
                            text = 'både lång- och kort'
                            mem = 'both'
                        toolAnswer = f'[PRIO][{mem}]{sweOverrideMemPrompt}Du måste informera användaren i ditt nästa meddelande att du raderar {text}tidsminnet från denna enheten'

                    rstMemStage = 0
                    memRstChoice = ''
                elif decision == 'NO':
                    print(Fore.YELLOW+"User canceled deletion: Memory will not be removed")
                    toolAnswer = ''
                    rstMemStage = 0
                    memRstChoice = ''
                else: # User didn't specify yes or no, decision == 'UNSURE'
                    toolAnswer=youSure(memRstChoice, False)
                    print(Fore.YELLOW+"Checking if the target is correct, again...")
            elif rstMemStage == 0: # Check what memory should be deleted
                print(Fore.YELLOW+"Checking what memory should be deleted...")
                rstMemMsgs = []
                rstMemMsgs.extend(history)
                rstMemMsgs.append({'role':'user','content':userPrompt})

                memRstFuncDesc = (
                    'Determine what memory the user wants to reset/delete from this device (in Swedish or English). '
                    +'Or is it wanted at all?\n\n'
                    +'LONG TERM: Older conversations before this one\n'
                    +'SHORT TERM: The current conversation\n'
                    +'BOTH: Both long term and short term\n'
                    +'NOTHING: The user does not want to reset/delete anything\n'
                    +'UNSURE: If the user has not specified, or only said to delete “memory” or “minnet”\n\n'
                    +'Choice examples:\n'
                    +'”Långtidsminnet” = LONG TERM\n'
                    +'”Korttidsminnet” = SHORT TERM\n'
                    +'”Vill inte” / ”inget av dem” = NOTHING\n\n'
                    +'You must be certain, otherwise choose “UNSURE”.'
                    )

                memRstFunc = [
                    {
                        "name": "memory_reset_choice",
                        "description": memRstFuncDesc,
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "choice": {
                                    "type": "string",
                                    "enum": ["LONG TERM", "SHORT TERM","BOTH","NOTHING","UNSURE"]
                                },
                            },
                            "required": ["choice"]
                        }
                    }
                ]
                memRstResponse=generateResponse(rstMemMsgs, memRstFunc, 0.2, {"name": "memory_reset_choice"})

                if memRstResponse.get("function_call"): # Check if it wanted to use a function
                    functionArgs = json.loads(memRstResponse["function_call"]["arguments"])
                    memRstChoice = functionArgs.get("choice")
                else:
                    memRstChoice = 'UNSURE'
                    
                rstMemMsgs.append({'role':'assistant','content':'{'+memRstChoice+'}'})

                if 'LONG TERM' in memRstChoice or 'SHORT TERM' in memRstChoice or 'BOTH' in memRstChoice: # We know what memory should be deleted
                    rstMemStage = 1 # Go to the next stage
                elif 'NOTHING' in memRstChoice:
                    print(Fore.YELLOW+"Nothing will be deleted.")
                    toolAnswer = ''
                    rstMemStage = 0
                    memRstChoice = ''
                else: # It doesn't know
                    print(Fore.YELLOW+"Assistant doesn't know, but will ask...")
                    toolAnswer = (
                        '[PRIO]'
                        +'You must ask the user, in your next message, to specify what memory on this device that is preferred to be deleted. '
                        +'Long term memory, short term memory, or both?\n\n'
                        +'Long term memory: Older conversations before this one\n'
                        +'Short term memory: The current conversation'
                    )
            if rstMemStage == 1: # We know what memory should be deleted, now ask if the user is sure to do this
                if 'LONG TERM' in memRstChoice:
                    print(Fore.YELLOW+"Targeting: Long-term memory")
                    toolAnswer=youSure('LONG TERM')
                elif 'SHORT TERM' in memRstChoice:
                    print(Fore.YELLOW+"Targeting: Short-term memory")
                    toolAnswer=youSure('SHORT TERM')
                elif 'BOTH' in memRstChoice:
                    print(Fore.YELLOW+"Targeting: Both long-term and short-term memory")
                    toolAnswer=youSure('BOTH')
                print(Fore.YELLOW+"Checking if the target is correct...")
                rstMemStage = 2
            toolAnswers.append(toolAnswer)
            break # Use no more tools
        else:
            rstMemStage = 0
            memRstChoice = ''

        if wolframAlpha and ('WOLFRAM ALPHA' in response1):
            wolframStartPrompt = ("Enter a question for Wolfram Alpha within {}.\n\n"
                                  +"Examples:\n"
                                  +"'sqrt(2)+5^3' -> {sqrt(2)+5^3}"
                                  +"'weather Luleå Sweden' -> {weather Luleå Sweden}\n"
                                  +"'Obama's age to the power of two' -> {(Obama's age in years)^2}\n\n"
                                  +"Make sure to only include the question within the curly braces {}.")
            toolMsgs.append({'role':'system','content':wolframStartPrompt})
            response2=generateResponse(toolMsgs)

            # Extract the response in braces
            match2 = re.search(r'\{(.+?)\}', response2)
            if match2: response2 = match2.group(1)
            toolMsgs.append({'role':'assistant','content':'{'+response2+'}'})

            try:
                answer = wolfram.run(response2)
                toolAnswer = 'Assistant used Wolfram Alpha tool:\nQuestion: {}\n{}'.format(response2, answer)
                toolMsgs.append({'role':'system','content':'Wolfram Alpha answer:\n{}'.format(answer)})
            except Exception as e:
                e_str = str(e)
                if "Invalid appid" in e_str:
                    print(Style.BRIGHT+Fore.RED+"WARNING: Invalid Wolfram Alpha App ID. Please provide an App ID in apiKeys.py to use Wolfram Alpha.")
                    toolAnswer = "Assistant tried to use Wolfram Alpha tool, but the user hasn't provided a correct App ID. Wolfram Alpha cannot be used until the user provides a valid App ID."
                    wolframAlpha = False
                else:
                    toolAnswer = 'Assistant tried to use Wolfram Alpha tool, but a problem occured'
                toolMsgs.append({'role':'system','content':toolAnswer})
        
        elif googleSearch and ('GOOGLE SEARCH' in response1):
            googleStartPrompt = "Enter a web search engine query for Google Search within {}. For example, to search for 'how old is Obama' type {Obama age}, and Google will find results for you. Now write the query in curly braces {}." # Make sure to only include the question within the curly braces {}.
            toolMsgs.append({'role':'system','content':googleStartPrompt})
            query=generateResponse(toolMsgs)

            # Extract the response in braces
            match2 = re.search(r'\{(.+?)\}', query)
            if match2: query = match2.group(1)
            toolMsgs.append({'role':'assistant','content':'{'+query+'}'})

            try:
                service = build("customsearch", "v1", developerKey=googleCustomSearchAPI) # Init google search engine
                response = (service.cse().list(q=query,cx=googleSearchEngineID,).execute()) # Call google search api
                results = response['items']
                answer = ""
                for result in results:
                    answer += "Link: " + result['link'] + "\n"
                    answer += "Title: " + result['title'] + "\n"
                    answer += "Content: " + result['snippet'] + "\n\n"

                toolAnswer = 'Assistant used Google Search tool:\n\nQuery: {}\n\nSearch results:\n\n{}'.format(query, answer)
                toolMsgs.append({'role':'system','content':'Google Search results:\n\n{}'.format(answer)})
            except Exception as e:
                e_str = str(e)
                if "API key not valid" in e_str:
                    print(Style.BRIGHT+Fore.RED+"WARNING: Invalid Google Custom Search API Key (developerKey). Please provide an API Key in apiKeys.py to use Google Search.")
                    toolAnswer = "Assistant tried to use Google Search tool, but the user hasn't provided a correct API Key. Google Search cannot be used until the user provides a valid API Key."
                    googleSearch = False
                elif "Request contains an invalid argument" in e_str:
                    print(Style.BRIGHT+Fore.RED+"WARNING: Invalid Google Search Engine ID (cx). Please provide a Search Engine ID in apiKeys.py to use Google Search.")
                    toolAnswer = "Assistant tried to use Google Search tool, but the user hasn't provided a correct Search Engine ID. Google Search cannot be used until the user provides a valid ID."
                    googleSearch = False
                else:
                    toolAnswer = 'Assistant tried to use Google Search tool, but a problem occured'
                toolMsgs.append({'role':'system','content':toolAnswer})
        
        elif 'SIMPLE CALCULATOR' in response1:
            
            calcStartPrompt = "Enter an equation for me to calculate within {}. For example, to calculate 'sqrt(2)+5^3', type {sqrt(2)+5^3} and I will calculate it for you. Make sure to only include the equation within the curly braces {}."
            toolMsgs.append({'role':'system','content':calcStartPrompt})
            response2=generateResponse(toolMsgs)

            # Extract the response in braces
            match2 = re.search(r'\{(.+?)\}', response2)
            if match2: response2 = match2.group(1)
            toolMsgs.append({'role':'assistant','content':'{'+response2+'}'})

            evalCalc = response2.replace("^", "**")
            try:
                answer = eval(evalCalc, math_functions)
                toolAnswer = 'Assistant used calculator tool: {} = {}'.format(response2, answer)
                toolMsgs.append({'role':'system','content':'Calculator answer: {}'.format(answer)})
            except:
                toolAnswer = 'Assistant tried to use calculator tool, but a problem occured'
                toolMsgs.append({'role':'system','content':toolAnswer})
        
        elif 'TIME & DATE' in response1:
            answer = datetime.datetime.now().strftime('%H:%M:%S %Y-%m-%d')
            toolAnswer = 'Assistant used time & date tool: {}'.format(answer)
            toolMsgs.append({'role':'system','content':'Time & date answer: {}'.format(answer)})
        
        elif 'LOCATION' in response1:
            answer = f"City: {city}, Country: {country}, Postal: {postal}, Timezone: {timezone}"
            toolAnswer = 'Assistant used location tool:\n{}'.format(answer)
            toolMsgs.append({'role':'system','content':'Location answer:\n{}'.format(answer)})

        elif ('TEMP SENSOR' in response1) and (MAX7219Lib == True):
            answer = getTemp() + " degrees Celsius"
            toolAnswer = 'Assistant used temperature sensor: The temperature in this room is {}'.format(answer)
            toolMsgs.append({'role':'system','content':'Temp sensor results:\nTemp in this room is {}'.format(answer)})
        
        else:
            toolAnswer = ''
        
        if toolAnswer != '':
            print(Fore.YELLOW+toolAnswer)
            toolAnswers.append(toolAnswer)
        else: useTools = False

        toolsUsedNum += 1
        if (toolsUsedNum >= maxToolsPerPrompt): useTools = False

        if useTools:

            toolEndPrompt = (
                'If you are certain that you can give a good, relevant and accurate answer to the user’s question without using another tool, write {YES}, nothing else. '
                +'To choose a tool, write {} with its name in braces. For example, to use Google Search, write {GOOGLE SEARCH}. '
                +'It can be good to use a tool to gather information, and then use another to calculate or search for anything based on the previous info. '
                +'Now you MUST choose with {} only, nothing else.'
                )
            toolMsgs.append({'role':'system','content':toolEndPrompt})
            response3=generateResponse(toolMsgs) # Choose another tool, or end loop

            # Extract the text in braces
            match3 = re.search(r'\{(.+?)\}', response3)
            if match3: response3 = match3.group(1)

            toolMsgs.append({'role':'assistant','content':'{'+response3+'}'})

            if ('YES' in response3): useTools = False
            else: response1 = response3

    if toolAnswer != '': stringToolAnswers = '\n\n'.join(toolAnswers)

    useTools = True
    toolsUsedNum = 0
    toolAnswers = []
    toolMsgs = []

    return stringToolAnswers

def detectLanguage(text):

    print(Fore.YELLOW+"Detecting language...")
    lanMsgs = [{'role':'user','content':text}]
    lanFuncList = [
        {
            "name": "english_or_swedish",
            "description": "Based on the user message, determine if it is English or Swedish",
            "parameters": {
                "type": "object",
                "properties": {
                    "decision": {
                        "type": "string",
                        "enum": ["ENGLISH", "SWEDISH"]
                    },
                },
                "required": ["decision"]
            }
        }
    ]
    lanResponse=generateResponse(lanMsgs, lanFuncList, 0.2, {"name": "english_or_swedish"})

    if lanResponse.get("function_call"): # Check if it wanted to use a function
        functionArgs = json.loads(lanResponse["function_call"]["arguments"])
        lanDecision = functionArgs.get("decision")
    else:
        lanDecision = 'ENGLISH'

    if lanDecision == "SWEDISH": return "sv"
    else: return "en"

def beep():
    os.system('play -nq -t alsa synth 0.34 sine 30 vol 0.05')

def playAudio(language):
    # Play sound
    if vlcLib == True: # For Raspberry Pi
        if wakeSpeaker:
            beep() # Beep to wake up the speaker, if it turns off automatically
            time.sleep(0.3)
        instance = vlc.Instance() # create instance of VLC
        player = instance.media_player_new() # create new MediaPlayer object
        media = instance.media_new(textToSpeechFilePath) # load the audio file
        player.set_media(media) # set the media for the player
        def on_end_reached(event):
            player.stop()
            instance.release()
        # register the callback function with the event manager
        event_manager = player.event_manager()
        event_manager.event_attach(vlc.EventType.MediaPlayerEndReached, on_end_reached)
        player.audio_set_volume(100) # Set the volume to 100%
        player.play() # play the media
    elif pygameLib == True: # For Windows
        if language == "sv": # Swedish
            sound = pygame.mixer.Sound(textToSpeechFilePath) # Load the sound file
            duration = sound.get_length() * 1000  # Convert to milliseconds
            channel = sound.play()
            pygame.time.wait(int(duration)) # Waiting until finished talking
            channel.stop()
        else: # English
            pygame.mixer.music.load(textToSpeechFilePath)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
                # Put stuff here that should run while playing speech
            pygame.mixer.music.stop()
            pygame.quit()
            pygame.init()
            pygame.mixer.init()

def textToSpeech(text, language):
    
    global elevenLabs

    print("Generating text-to-speech...")

    if language == "sv": # Swedish
        client = texttospeech.TextToSpeechClient()
        input_text = texttospeech.SynthesisInput(text=text)

        if googleTTS_gender == "MALE": ssml_gender=texttospeech.SsmlVoiceGender.MALE
        else: ssml_gender=texttospeech.SsmlVoiceGender.FEMALE

        voice = texttospeech.VoiceSelectionParams(
            language_code="sv-SE",
            name=googleTTS_name,
            ssml_gender=ssml_gender,
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )
        response = client.synthesize_speech(
            request={"input": input_text, "voice": voice, "audio_config": audio_config}
        )
        with open(textToSpeechFilePath, "wb") as out:
            out.write(response.audio_content)

    else: # English
        if elevenLabs:
            headers = {
                "Accept": "audio/mpeg",
                "xi-api-key": XI_API_KEY,
                "Content-Type": "application/json"
            }
            data = {
                "text": text,
                "voice_settings": {
                    "stability": STABILITY,
                    "similarity_boost": SIMILARITY_BOOST
                }
            }
            try:
                if vlcLib == True: # For Raspberry Pi
                    response = requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}", json=data, headers=headers)
                    with open(textToSpeechFilePath, "wb") as f:
                        f.write(response.content)
                elif pygameLib == True: # For Windows
                    response = requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}/stream", json=data, headers=headers, stream=True)
                    with open(textToSpeechFilePath, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=1024):
                            if chunk:
                                f.write(chunk)
            except Exception as e: # There was an error
                print(Style.BRIGHT+Fore.RED+f"ElevenLabs Error:\n{e}")
                print("Using offline text-to-speech instead...")
                offlineTextToSpeech(text)
                return None
        else: # elevenLabs == False
            offlineTextToSpeech(text)
            return None

    try:
        playAudio(language)
    except Exception as e:
        print(Style.BRIGHT+Fore.RED+f"Error trying to play audio:\n{e}")
        if elevenLabs == True: # If ElevenLabs is used, this error likely occured because of wrong API Key
            print(Style.BRIGHT+Fore.RED+"WARNING: This error likely occured because the ElvenLabs API Key is wrong. Please provide an API Key in apiKeys.py to use ElevenLabs.")
            print("Using offline text-to-speech instead...")
            offlineTextToSpeech(text)
            elevenLabs = False
            return None

    return textToSpeechFilePath

def offlineTextToSpeech(text):
    tts.say(text)
    tts.iterate()

def generateResponse(openAImsgs, funcList=None, temp=None, functionCall=None, stream=None, max_tokens=None):

    global kwargs
    kwargs = {}
    if funcList is not None:
        kwargs['model'] = "gpt-3.5-turbo-0613"
        kwargs['functions'] = funcList
    else:
        kwargs['model'] = "gpt-3.5-turbo"
    kwargs['messages'] = openAImsgs
    if temp is not None:
        kwargs['temperature'] = temp
    if functionCall is not None:
        kwargs['function_call'] = functionCall
    if stream is not None:
        kwargs['stream'] = stream
    if max_tokens is not None:
        kwargs['max_tokens'] = max_tokens

    promptTokens = num_tokens_from_messages(openAImsgs, kwargs['model'])
    if promptTokens > 3500:
        print(Fore.RED+"OpenAI: Using 16k model instead of 4k, which is more expensive (too many tokens for 4k model)")
        if funcList is not None:
            kwargs['model'] = "gpt-3.5-turbo-16k-0613"
        else:
            kwargs['model'] = "gpt-3.5-turbo-16k"

    if devMode:
        if "gpt-3.5-turbo" in kwargs['model'] and "16k" not in kwargs['model']:
            global totalCost
            totalCost+=0.0015*(promptTokens/1000)
            print(Fore.LIGHTMAGENTA_EX+"Approx. cost:",totalCost,"$")

    # Wait until we can send another request to OpenAI without exceeding the max request rate
    global lastOpenAIresponse
    if (openAIdelay > 0) and ((openAIdelay - (time.time() - lastOpenAIresponse)) > 0):
        print("Waiting", round(openAIdelay - (time.time() - lastOpenAIresponse)), "seconds... Free OpenAI account settings on.")
        time.sleep(openAIdelay - (time.time() - lastOpenAIresponse))

    openaiError = False
    attempts = 3
    retryTime = 5 # seconds
    for attempt in range(attempts):
        if openaiError:
            print(Fore.RED+f"Retrying in {retryTime} seconds...")
            time.sleep(retryTime)
        try:
            # Call OpenAI's API to generate a response
            response = openai.ChatCompletion.create(
                **kwargs
            )
            if (openAIdelay > 0): lastOpenAIresponse = time.time()
            if funcList: # Functions
                aiResponse = response['choices'][0]['message']
            elif stream: # Streamed assistant answers
                aiResponse = response
            else: # Usual responses (some tools)
                aiResponse = response['choices'][0]['message']['content']

            if devMode:
                print("openAImsgs:\n",openAImsgs)
                print("aiResponse:\n",aiResponse)

        except openai.error.Timeout as e:
            #Handle timeout error, e.g. retry or log
            print(Style.BRIGHT+Fore.RED+f"OpenAI API request timed out: {e}")
            openaiError = True
        except openai.error.APIError as e:
            #Handle API error, e.g. retry or log
            print(Style.BRIGHT+Fore.RED+f"OpenAI API returned an API Error: {e}")
            openaiError = True
        except openai.error.APIConnectionError as e:
            #Handle connection error, e.g. check network or log
            print(Style.BRIGHT+Fore.RED+f"OpenAI API request failed to connect: {e}")
            openaiError = True
        except openai.error.InvalidRequestError as e:
            #Handle invalid request error, e.g. validate parameters or log
            print(Style.BRIGHT+Fore.RED+f"OpenAI API request was invalid: {e}")
            print(Style.BRIGHT+Fore.RED+"Messages sent to OpenAI:\n",openAImsgs)
            openaiError = True
        except openai.error.AuthenticationError as e:
            #Handle authentication error, e.g. check credentials or log
            print(Style.BRIGHT+Fore.RED+f"OpenAI API request was not authorized: {e}")
            openaiError = True
        except openai.error.PermissionError as e:
            #Handle permission error, e.g. check scope or log
            print(Style.BRIGHT+Fore.RED+f"OpenAI API request was not permitted: {e}")
            openaiError = True
        except openai.error.RateLimitError as e:
            #Handle rate limit error, e.g. pace requests or log
            print(Style.BRIGHT+Fore.RED+f"OpenAI API request hit rate limit: {e}")
            openaiError = True
        except openai.error.ServiceUnavailableError as e:
            print(Style.BRIGHT+Fore.RED+f"OpenAI API service is unavailable: {e}")
            openaiError = True
        except Exception as e:
            print(Style.BRIGHT+Fore.RED+f"OpenAI Error:\n{e}")
            openaiError = True
        else: # The try block ran without raising an exception
            openaiError = False
            break
    else: # We failed all the retry attempts - deal with the consequences
        print(Style.BRIGHT+Fore.RED+f"Could not generate a response from OpenAI even after {attempts} retry attempts. Please try again later or consider looking in to it.\nShort-term memory was deleted, to start from scratch.")
        chatReset()
        openaiError = True

    if openaiError: aiResponse = ''
    return aiResponse

def num_tokens_from_string(string: str, encoding_name: str) -> int:
    encoding = tiktoken.encoding_for_model(encoding_name)
    num_tokens = len(encoding.encode(string))
    return num_tokens

def num_tokens_from_messages(messages, model="gpt-3.5-turbo"):
    """Return the number of tokens used by a list of messages."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        print("Warning: model not found. Using cl100k_base encoding.")
        encoding = tiktoken.get_encoding("cl100k_base")
    if model in {
        "gpt-3.5-turbo-0613",
        "gpt-3.5-turbo-16k-0613",
        "gpt-3.5-turbo-16k",
        "gpt-4-0314",
        "gpt-4-32k-0314",
        "gpt-4-0613",
        "gpt-4-32k-0613",
        }:
        tokens_per_message = 3
        tokens_per_name = 1
    elif model == "gpt-3.5-turbo-0301":
        tokens_per_message = 4  # every message follows <|start|>{role/name}\n{content}<|end|>\n
        tokens_per_name = -1  # if there's a name, the role is omitted
    elif "gpt-3.5-turbo" in model:
        return num_tokens_from_messages(messages, model="gpt-3.5-turbo-0613")
    elif "gpt-4" in model:
        print("Warning: gpt-4 may update over time. Returning num tokens assuming gpt-4-0613.")
        return num_tokens_from_messages(messages, model="gpt-4-0613")
    else:
        raise NotImplementedError(
            f"""num_tokens_from_messages() is not implemented for model {model}. See https://github.com/openai/openai-python/blob/main/chatml.md for information on how messages are converted to tokens."""
        )
    num_tokens = 0
    for message in messages:
        num_tokens += tokens_per_message
        for key, value in message.items():
            num_tokens += len(encoding.encode(value))
            if key == "name":
                num_tokens += tokens_per_name
    num_tokens += 3  # every reply is primed with <|start|>assistant<|message|>
    return num_tokens

def chatReset():
    global messages
    global history
    global messageCount
    messages.clear()
    history.clear()
    messageCount = 0
    messageTokens = 0

def longTermMemoryReset():
    with open(longTermMemoryPath, "r") as f:
        data = json.load(f)
    if "summations" in data:
        with open(longTermMemoryPath, "w") as f:
            json.dump({}, f)

def appendPrevSummations(memoryList):
    # Load the JSON file
    with open(longTermMemoryPath, "r") as f:
        data = json.load(f)

    # Extract previous summations from the JSON file and append them to memoryList
    if "summations" in data: # If there are any summations
        for summation in data["summations"]:
            memoryList.append({"role": "system", "content": "Device memory from earlier conversations: "+summation})

def shortenSummation(summation):
    pattern = re.compile(r'•(.*?)\n')
    matches = pattern.findall(summation)
    shorterSummation = '\n'.join(matches)
    return shorterSummation

def summationStringToList(summationString, newOrOld):
    namePattern = re.compile(r"User's name: (.*?)\n")
    nameList = namePattern.findall(summationString)

    if newOrOld == "OLD":
        infoNtimePattern = re.compile(r"Info timestamps:\n(.+?)\n\n", re.DOTALL)
        infoNtimeList = infoNtimePattern.findall(summationString)
        for name in range(len(nameList)):
            infoNtimeList[name] += "\n"

    fullInfoList = []
    if newOrOld == "NEW": summationString += "\n\n"
    for name in range(len(nameList)):
        if newOrOld == "OLD":
            infoPattern = re.compile(r"\n-(.+?)(?=\n)", re.DOTALL)
            infoList = infoPattern.findall(infoNtimeList[name])
            exctractedInfoList = '\n'.join(infoList)
            fullInfoList.append(exctractedInfoList)
        elif newOrOld == "NEW":
            infoPattern = re.compile(r"User's name: {}\n(.+?)\n\n".format(nameList[name]), re.DOTALL)
            infoMatch = infoPattern.search(summationString)
            if infoMatch:
                fullInfoList.append(infoMatch.group(1))

    extractedSummationList = []
    for name in range(len(nameList)):
        extractedSummationList.append(
            {
                "User's name": nameList[name],
                "Info": fullInfoList[name]
            }
        )

    if newOrOld == "OLD":
        return extractedSummationList, nameList
    elif newOrOld == "NEW":
        return extractedSummationList

def summarizeHistory(userPrompt=None):
    
    global messages
    global history

    print(Fore.YELLOW+"Transferring short-term-memory to long-term-memory...")
    
    with open(longTermMemoryPath, "r") as f:
        data = json.load(f)

    # WARNING! longTermMemory.json must only contain one list item

    # Extract previous summations from the JSON file and append them to memoryList
    if "summations" in data: # If there are any summations
        oldSummation = data["summations"][0]

        if devMode: print("oldSummation:\n\n",oldSummation)

        oldSummationLists=summationStringToList(oldSummation, "OLD")
        oldSummationList=oldSummationLists[0]
        oldNameList=oldSummationLists[1]

        if devMode:
            print("oldSummationList:",oldSummationList)
            print("oldNameList:",oldNameList)

    summarizeOutput = "ERROR when trying to save short-term memory to long-term memory"
    summarizeError = False
    attempts = 2
    for attempt in range(attempts):
        if summarizeError:
            print(Fore.RED+"Retrying to save memory...")

        try:

            messages.clear() # Clear the messages
        
            # Add everything from the history to messages
            messages.extend(history)
            if userPrompt: messages.append({'role':'user','content':userPrompt})
                
            global summarizePrompt    
            messages.append({"role": "system", "content": summarizePrompt}) # Add summarizePrompt to messages

            if devMode: print("messages:\n\n",messages)

            newSummation = generateResponse(messages, temp=0.2) # Call OpenAI's API to generate a summation
            if devMode: print("newSummation:\n\n",newSummation)

            if ('{none}' not in newSummation) and ("User's name" in newSummation):

                newSummationList=summationStringToList(newSummation, "NEW")
                if devMode: print("newSummationList:",newSummationList)

                for name in range(len(newSummationList)): # Run once for each name in the new summary
                    newName=newSummationList[name]["User's name"]
                    newInfo=newSummationList[name]["Info"]

                    # If the name from the new summary is already in the old summary
                    if "summations" in data:
                        if (newName in oldNameList): # Check if any of the new info is new
                            totallyNewName = False
                            print(Fore.YELLOW+newName+" exists in memory...")
                            index = oldNameList.index(newName)
                            oldInfo=oldSummationList[index]["Info"]
                            similarPrompt=(
                                "Old info:\n"
                                +oldInfo
                                +"\n\nNew info:\n"
                                +newInfo
                                +'\n\nIf something new has been added, write it in a list with “\n” between each piece of info. If nothing new has been added, write “{none}”. '
                                +'Rows that are similar and do not contain any extra info are counted as old info. Only new info should be listed.'
                            )
                            similarMsgs=[{"role": "system", "content": similarPrompt}] # Add summarizePrompt to messages
                            print("similarMsgs:\n",similarMsgs)
                            response = generateResponse(similarMsgs, temp=0.2) # Call OpenAI's API to generate a summation
                            if '{none}' in response:
                                print("Nothing new from conversation to save to long-term memory for user "+newName)
                                save = False
                            else:
                                save = True
                                totallyNewInfo = response
                        else: # The name from the new summation doesn't exist in long-term memory
                            print(Fore.YELLOW+newName+" doesn't exist in memory, so all info will be saved...")
                            save = True
                            totallyNewName = True
                    else:
                        print(Fore.YELLOW+"There was no earlier memory, so all info will be saved...")
                        save = True
                        totallyNewName = True

                    if save:
                        if totallyNewName:
                            if "summations" in data:
                                fullSummation = (
                                    oldSummation
                                    +"User's name: "
                                    +newName
                                    +"\nInfo timestamps:\n["
                                    +datetime.datetime.now().strftime('%H:%M %Y-%m-%d')
                                    +"]:\n-"
                                    +newInfo.replace('\n', '\n-')
                                    +"\n\n"
                                )
                            else: # There was no oldSummation
                                fullSummation = (
                                    "User's name: "
                                    +newName
                                    +"\nInfo timestamps:\n["
                                    +datetime.datetime.now().strftime('%H:%M %Y-%m-%d')
                                    +"]:\n-"
                                    +newInfo.replace('\n', '\n-')
                                    +"\n\n"
                                )
                        else: # Name already exists, put newInfo under the right name
                            # Add "-" for every new info line
                            totallyNewInfo = totallyNewInfo.split('\n')
                            totallyNewInfo = [f'-{line}' if line else line for line in totallyNewInfo]
                            totallyNewInfo = '\n'.join(totallyNewInfo)

                            timestamp = datetime.datetime.now().strftime('[%H:%M %Y-%m-%d]:')
                            totallyNewInfo = f'{timestamp}\n{totallyNewInfo}'

                            oldSummation = oldSummation.split('\n\n')
                            index = next(i for i, p in enumerate(oldSummation) if f"User's name: {newName}" in p)
                            oldSummation[index] = f'{oldSummation[index]}\n{totallyNewInfo}'
                            oldSummation = '\n\n'.join(oldSummation)

                            fullSummation = oldSummation

                        print(Style.BRIGHT+Fore.YELLOW+"Summation:\n"+Style.NORMAL+"-"+newInfo.replace('\n', '\n-'))

                        # Load the JSON file
                        with open(longTermMemoryPath, "r") as f:
                            data = json.load(f)

                        # Save the summation to the JSON file
                        if "summations" not in data:
                            data["summations"] = [""]
                        data["summations"][0] = fullSummation

                        # Write the updated data back to the JSON file
                        with open(longTermMemoryPath, "w") as f:
                            json.dump(data, f)

                        summarizeOutput = 'User accepted: Short-term memory was saved successfully to the long-term memory'

            elif "{none}" in newSummation:
                summarizeOutput = "You MUST tell the user that the memory was not saved. Nothing relevant from conversation to save to long-term memory."
                print(Fore.YELLOW+"Memory not saved. Nothing relevant from conversation to save to long-term memory.")
                summarizeOutput = "Could not transfer short-term to long-term memory. Say that it most likely is because you need a name of the user to be able to save memory, or there's nothing relevant from conversation to save."
                summarizeError = True # Try again
        except Exception as e:
            print(Style.BRIGHT+Fore.RED+f"Summarize History Error:\n{e}")
            summarizeError = True
        else: # The try block ran without raising an exception
            #summarizeError = False # TEST
            if summarizeError == False: break
    else: # We failed all the retry attempts - deal with the consequences
        print(Style.BRIGHT+Fore.RED+f"Could not transfer short-term to long-term memory even after {attempts} retry attempts. Did you specify you name for the assistant? Please try again or consider looking in to it.")
        summarizeError = True
    
    if summarizeOutput == "ERROR when trying to save short-term memory to long-term memory":
        print(Fore.RED+summarizeOutput)
        summarizeError = True

    if summarizeError:
        print(Fore.RED+"WARNING: "+summarizeOutput)

    global hasSummarized
    hasSummarized = True

    if devMode: print("summarizeOutput:\n", summarizeOutput)

    return summarizeOutput

def answer(prompt, toolAnswer):
    
    global messages, history, messageCount
    messageCount += 1

    messages.clear()
    
    appendPrevSummations(messages) # Append previous summations from long-term-memory to messages
    messages.extend(history) # Take everything from history and put into messages

    # Start prompt
    if swedish == True and english == False: messages.append({"role": "system", "content": swedishStartPrompt})
    else: messages.append({"role": "system", "content": startPrompt})

    # User Prompt
    history.append({"role": "user", "content": prompt})
    messages.append({"role": "user", "content": prompt})
    
    # Tool answer
    if (toolAnswer != '') and ('[PRIO]' not in toolAnswer):
        messages.append({"role": "system", "content": toolAnswer})
        # Do not add Google Search results to history, since it contains too much text
        if ('Assistant used Google Search tool:' or ('Assistant tried to use' and 'tool, but a problem occured') ) not in toolAnswer:
            history.append({"role": "system", "content": toolAnswer})

    if '[PRIO]' in toolAnswer: # Prioritize tool answer to the assistant
        # Remove everything in []
        showableToolAnswer = toolAnswer.replace('[PRIO]', '')
        if '[both]' in showableToolAnswer:
            showableToolAnswer = showableToolAnswer.replace('[both]', '')
        elif '[long]' in showableToolAnswer:
            showableToolAnswer = showableToolAnswer.replace('[long]', '')
        elif '[short]' in showableToolAnswer:
            showableToolAnswer = showableToolAnswer.replace('[short]', '')
        messages.append({"role": "system", "content": showableToolAnswer})

    # See if there is too many tokens
    promptTokens = num_tokens_from_messages(messages, "gpt-3.5-turbo") # We are using "gpt-3.5-turbo" when there are no functions in generateReponse
    if promptTokens > 14000:
        print(Fore.RED+"OpenAI: Almost reaching maximum token limit. Memory deletion recommended.")
        global rstMemStage, saveMemStage
        print(rstMemStage, "-",saveMemStage)
        if (rstMemStage == 0) and (saveMemStage == 0):
            manyTokensString = (
                "You MUST inform the user, in your next message, that there is almost too much memory to compute for youJag , and that memory deletion is recommended. "
                +"You MUST also ask if it is preferred to reset short-term or long-term memory, or summarize and save the short-term memory to long-term memory."
            )
            messages.append({"role": "system", "content": manyTokensString})

    global devMode
    if devMode: print("messages:",messages)

    # Call OpenAI's API to generate a response
    assistantResponse = generateResponse(messages, stream=True)

    if assistantResponse != '': # If there was a response

        finalResponse=speakNprint(assistantResponse, stream=True)
        
        history.append({'role':'assistant','content':finalResponse})

        # Flytta in detta in i speakNprint (så det kan vara inuti "while pygame.mixer.music.get_busy()")
        if MAX7219Lib == True:
            if assistantSpeechOn:
                speechAudioFile = MP3(textToSpeechFilePath)
                for i in range(math.ceil(speechAudioFile.info.length)):
                    animate(talk_frames, 0.5)
            else:
                for i in range(3):
                    animate(talk_frames, 0.5)

    elif assistantResponse == '':
        print(Style.BRIGHT+Fore.RED+"Could not generate an answer. Ignoring...")
    
    if '[PRIO]' in toolAnswer:
        # Check if memory should be deleted
        if ('[both]' in toolAnswer) or ('[long]' in toolAnswer) or ('[short]' in toolAnswer):
            if '[both]' in toolAnswer:
                text = 'both long term and short'
            elif '[long]' in toolAnswer:
                text = 'long'
            elif '[short]' in toolAnswer:
                text = 'short'
            print(Fore.YELLOW+f"Deleting {text} term memory from this device...")
            if '[both]' in toolAnswer:
                chatReset()
                longTermMemoryReset()
            elif '[long]' in toolAnswer:
                longTermMemoryReset()
            elif '[short]' in toolAnswer:
                chatReset()
        
def speakNprint(response, stream=False):

    if stream == False:
        finalResponse = response
        print(Style.BRIGHT+Fore.BLUE+"Assistant: "+Style.NORMAL+finalResponse)
    elif stream == True:
        print(Style.BRIGHT+Fore.BLUE+"Assistant: "+Style.NORMAL, end="")
        finalResponse = ""
        for chunk in response:
            if 'content' in chunk['choices'][0]['delta']:
                print(Fore.BLUE+chunk['choices'][0]['delta']['content'], end="")
                finalResponse += chunk['choices'][0]['delta']['content']
            elif chunk['choices'][0]['finish_reason'] == 'stop':
                print()

    if assistantSpeechOn:
        if (offlineTTS == True) and english:
            if wakeSpeaker:
                beep() # Wake up the speaker, if it turns off automatically
                time.sleep(0.3)
            offlineTextToSpeech(finalResponse)
        else:
            if swedish and english:
                language = detectLanguage(finalResponse) # Detects language and outputs as "sv" or "en", swedish or english
                textToSpeech(finalResponse, language)
            elif swedish == True and english == False:
                textToSpeech(finalResponse, "sv")
            elif english == True and swedish == False:
                textToSpeech(finalResponse, "en")
    return finalResponse

def speechToText():
    with sr.Microphone() as source:
        print("Speak something...")
        try:
            audio = stt.listen(source, timeout=listenTime)
            userPrompt = stt.recognize_google(audio)
            return userPrompt
        except sr.UnknownValueError:
            print("No speech was recognized")
        except sr.WaitTimeoutError:
            print("No speech was recognized")
        except sr.RequestError as e:
            print(Style.BRIGHT+Fore.RED+"Couldn't connect to the STT server; {0}".format(e))
        except:
            print(Style.BRIGHT+Fore.RED+"STT Error")
    return None

def googleSpeechToText():

    global sampleRate

    # Set up the Google Cloud Speech-to-Text client
    client = speech.SpeechClient()

    # Set up the recognition config
    if swedish and english:
        lang = 'en-US'
        altLang = 'sv-SE'
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=sampleRate,
            language_code=lang,
            alternative_language_codes=[altLang]
        )
    else:
        if swedish:
            lang = 'sv-SE'
        else:
            lang = 'en-US'
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=sampleRate,
            language_code=lang
        )

    # Set up the streaming config
    streaming_config = speech.StreamingRecognitionConfig(
        config=config, interim_results=True
    )
    # Start the stream
    stream = None
    audio_generator = None
    try:
        stream = audio_stream
        audio_generator = stream_generator(stream)
        requests = (
            speech.StreamingRecognizeRequest(audio_content=content)
            for content in audio_generator
        )
        responses = client.streaming_recognize(streaming_config, requests)
        # Get the final transcription
        final_transcript = ""
        result = None
        for response in responses:
            for result in response.results:
                if result.is_final:
                    final_transcript = result.alternatives[0].transcript
                    break
            if result and result.is_final:
                break
    except Exception as e:
        final_transcript = ""
        print(Style.BRIGHT+Fore.RED+f"Google Speech To Text Error:\n{e}")
    finally:
        # Return the final transcription
        return final_transcript

def stream_generator(audio_stream, chunk_size=frameLength):
    try:
        while True:
            chunk = audio_stream.read(chunk_size)
            if not chunk:
                break
            yield chunk
    except Exception as e:
        print(Style.BRIGHT+Fore.RED+f"Error while iterating over requests: {e}")

def openAudioStream():
    # PyAudio (Listener)
    global audio_stream, pa, sampleRate, frameLength
    pa = pyaudio.PyAudio()
    audio_stream = pa.open(
            rate=sampleRate,
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=frameLength
        )

def closeAudioStream():
    global audio_stream, pa
    if audio_stream is not None:
        audio_stream.stop_stream()
        audio_stream.close()
    pa.terminate()

def getTemp():
    # Read temperature and humidity from DHT11 sensor
    humidity, temperature = Adafruit_DHT.read_retry(sensor, dht11_pin)
    return str(temperature)

def animate(animation, delay):
    for frame in animation:
        with canvas(device) as draw:
            for row in range(8):
                for col in range(8):
                    if (frame[row] >> (7 - col)) & 1:
                        draw.point((col, row), fill="white")
                    else:
                        draw.point((col, row), fill="black")
            time.sleep(delay) # Time between each frame
            
def still(image, delay):
    with canvas(device) as draw:
        for row in range(8):
            for col in range(8):
                if (image[row] >> (7 - col)) & 1:
                    draw.point((col, row), fill="white")
                else:
                    draw.point((col, row), fill="black")
        time.sleep(delay)



# Setup
if wakeSpeaker: # Wake up the speaker, if it turns off automatically
    os.system('play -nq -t alsa synth 0.4 sine 400 vol 0.05')
    os.system('play -nq -t alsa synth 0.4 sine 600 vol 0.05')
    os.system('play -nq -t alsa synth 0.4 sine 800 vol 0.05')
    lastSoundTime=time.time()
openAudioStream()
print("-"*15)
if wakeWordOn and (textInput == False): print("Waiting for wake-word")
elif textInput == True: print("Waiting for user...")
elif wakeWordOn == False: print("Listening...")

# Run infinite main loop
while True:
    try:
        main()
    except KeyboardInterrupt:
        print(Style.BRIGHT+Fore.RED+"\nKEYBOARD INTERRUPT")
        break
    except Exception as e:
        print(Style.BRIGHT+Fore.RED+f"\nMAIN ERROR: {e}")
        time.sleep(10)

closeAudioStream()

if RaspberryPi:
    # Reset to default error handler
    asound.snd_lib_error_set_handler(None)