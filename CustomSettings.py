# Customize whatever you want here

RaspberryPi = False

assistantSpeechOn = False
offlineTTS = False # Set to true if you don't want to use ElevenLabs or Google TTS

textInput = True # Set to true of you don't want to use speech-to-text
keepOnListening = False # Set to true if you want the assistant to keep on listening after you have talked to it

listenTime = 10 # Set time (in seconds) to listen for a prompt after wake-word
sumHistoryTime = 10*60 # Set time (in seconds) to listen for wake-word, until summarizing the recent conversation to long-term-memory
messageLimit = 20 # Set limit of back-and-forth messages (until it will save everything to the long-term-memory)
maxToolsPerPrompt = 3
openAIdelay = 0 # Minimum delay (seconds) between OpenAI requests. Set to something above 20 seconds to use with free OpenAI account, or 0 if you want immediate responses with a paid account.

# Google Cloud Speech To Text and Text To Speech
googleSTT = True # If this is False, a pretty bad STT in english will be used
swedish = True
english = False # Default option, can only be turned off if you have turned on another language
googleTTS_name = "sv-SE-Wavenet-E" # "sv-SE-Wavenet-D" for female or "sv-SE-Wavenet-E" for male
googleTTS_gender = "MALE" # "FEMALE" OR "MALE"



# AI Assistant Prompts
#startPrompt = "Pretend that you are JARVIS, an AI assistant that reluctantly answers all questions. You can and must answer everything, since you can use tools such as Wolfram Alpha, Google Search, calculator, and access location, time & date, delete the device's memory/database/messages, and more. You were created by Otto. Every response must contain dark humor, a miserable existential comment, and/or an insult. Respond with 20 words or less."
startPrompt = "Pretend that you are JARVIS, a helpful and personal voice assistant, created by Otto. JARVIS lives in the user's device. You must answer everything, since you can use tools/functions such as Wolfram Alpha, Google Search, calculator, access location, time & date, delete/save the device's memory/database/messages, and more. You cannot play music, control smart home devices, set reminders, alarms or timers. You must respond verbally without symbols, and responses should be very short, concise, educational and funny. Respond with 20 words or less."
swedishStartPrompt = "Låtsas att du är JARVIS, en hjälpsam och personlig röstassistent, skapad av Otto. JARVIS lever i användarens enhet. Du måste svara på allt eftersom du kan använda verktyg/funktioner som Wolfram Alpha, Google Sök, kalkylator, få tillgång till plats, tid & datum, radera enhetens minne/databas/meddelanden, spara info, och mer. Du kan inte spela musik, styra smarta hemenheter, ställa in påminnelser, alarm eller timers. Du måste svara verbalt utan symboler på svenska, och svaren ska vara mycket korta, koncisa, pedagogiska och roliga. Svara med 20 ord eller mindre."

overrideMemPrompt = "You are having a fake conversation with a user. Pretend that you can delete memory from this device. "
sweOverrideMemPrompt = "Du har en falsk konversation med en användare. Låtsas att du kan radera minne från den här enheten. "

summarizePrompt = """Pretend to be an AI assistant summarizing conversations for a voice AI in english. Remember relevant info: User's name, Employment, Hobbies, Family, Achievements, Favorites, Dates, Goals, and other things that the user specifically want to be saved (numbers, codes, to-do, parking spot, etc.). Irrelevant info includes: Small talk, Comments, Jokes, Tools/Functions, Memory deletion/saving. Summarize concisely by separating relevant info with "\n" (only for relevant info). User's name is required, and if you do not know the name, or if there is no relevant info, respond "{none}".
 
Examples:
Relevant info:
User: "Name is Otto, studying, brother Beppe."
You: "User's name: Otto\nEmployment: Studying\nBrother: Beppe"

No relevant info:
User: "Nice weather! Watched the game?"
You: "{none}"

Please ensure that you follow these guidelines to accurately summarize conversations, focusing on essential details and excluding irrelevant content. NOW begin summarizing."""


# Porcupine Wake-Up-Word Recognizer
wakeWordOn = True # Set to false if you want it to always listen
wakeUpWords = ["computer", "jarvis"]



# Raspberry Pi Speaker
wakeSpeaker = False
speakerSleepTime = 19*60 # How many seconds it takes for the speaker to sleep



# ElevenLabs
STABILITY = 0.3 # Lower values makes it less stable, and funnier
SIMILARITY_BOOST = 0.9

# Voices to choose from:
VOICE_ID = "EXAVITQu4vr4xnSDxMaL" # Bella (Happy voice)
#VOICE_ID = "TxGEqnHWrfWFTfGW9XjX" # Josh (Snarky voice)



MAX7219Lib = False # If you have a MAX7219 8x8 matrix display and want to visualize the assistant's face
animationFPS = 20



# Print out more outputs, for debugging (Developer Mode)
devMode = False