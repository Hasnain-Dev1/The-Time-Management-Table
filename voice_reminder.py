import speech_recognition as sr
import pyttsx3
import time

# Setup TTS engine
engine = pyttsx3.init()
engine.setProperty('rate', 170)  # Speed
engine.setProperty('volume', 1.0)  # Volume

# Wake word
WAKE_WORD = "hey sweetbot"

# Speak text
def speak(text):
    print("🤖 SweetBot:", text)
    engine.say(text)
    engine.runAndWait()

# Process the command after wake word
def respond_to_command():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("🎤 Listening for your command...")
        r.adjust_for_ambient_noise(source)
        try:
            audio = r.listen(source, timeout=5)
            command = r.recognize_google(audio)
            print("🗣️ You said:", command)

            # 🔁 Add your command logic here
            if "how are you" in command.lower():
                speak("I'm great! How can I assist you today?")
            elif "your name" in command.lower():
                speak("My name is SweetBot, your voice assistant.")
            else:
                speak("Sorry, I didn't understand. Can you repeat?")
        except sr.UnknownValueError:
            speak("Sorry, I couldn't understand that.")
        except sr.WaitTimeoutError:
            speak("No input detected.")
        except sr.RequestError:
            speak("Network error. Please check your connection.")

# Wake word listener
def listen_for_wake_word():
    recognizer = sr.Recognizer()
    mic = sr.Microphone()

    with mic as source:
        recognizer.adjust_for_ambient_noise(source)
        print("👂 Waiting for wake word... Say 'Hey SweetBot'")

        while True:
            try:
                audio = recognizer.listen(source, timeout=None)
                phrase = recognizer.recognize_google(audio).lower()
                print("🔊 Heard:", phrase)

                if WAKE_WORD in phrase:
                    speak("Yes? I'm listening...")
                    respond_to_command()

            except sr.UnknownValueError:
                pass  # Ignore non-understandable audio
            except sr.RequestError:
                speak("⚠️ Network error occurred. Please check your connection.")

# Run the assistant
if __name__ == "__main__":
    listen_for_wake_word()
