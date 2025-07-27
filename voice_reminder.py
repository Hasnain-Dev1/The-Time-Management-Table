import speech_recognition as sr
import pyttsx3
import asyncio
import websockets
import json
import time
from datetime import datetime

# --- Global WebSocket Clients Set ---
connected_clients = set()

# --- Speech Synthesis Setup ---
engine = pyttsx3.init()
engine.setProperty('rate', 170)  # Speed of speech
engine.setProperty('volume', 1.0)  # Volume

# --- Voice Assistant Settings ---
WAKE_WORD = "hey sweetbot"

# --- WebSocket Communication Functions ---
async def register_websocket(websocket):
    """Registers a new WebSocket connection."""
    connected_clients.add(websocket)
    print(f"WebSocket client connected: {websocket.remote_address}. Total clients: {len(connected_clients)}")
    try:
        await websocket.wait_closed()
    finally:
        connected_clients.remove(websocket)
        print(f"WebSocket client disconnected: {websocket.remote_address}. Total clients: {len(connected_clients)}")

async def send_to_browser(message_data):
    """Sends a JSON message to all connected WebSocket clients (browsers)."""
    if not connected_clients:
        print("No browser clients connected to send message.")
        return

    message = json.dumps(message_data)
    # Using asyncio.gather to send to all clients concurrently
    # and return_exceptions=True to handle individual client errors without stopping all
    try:
        await asyncio.gather(
            *(client.send(message) for client in connected_clients),
            return_exceptions=True
        )
        print(f"Sent to browser: {message_data.get('action', 'Unknown Action')}")
    except Exception as e:
        print(f"Error sending message to browser: {e}")

# --- Voice Assistant Core Functions ---
def speak(text):
    """Speaks the given text using the TTS engine."""
    print("🤖 SweetBot:", text)
    engine.say(text)
    engine.runAndWait()

# A simple lock to prevent overlapping speech recognition attempts
# This is crucial because listen() is blocking and could cause issues if called again
recognizer_lock = asyncio.Lock()

async def respond_to_command(recognizer, source):
    """
    Listens for and processes a command after the wake word.
    """
    async with recognizer_lock: # Acquire lock, ensures only one command processed at a time
        try:
            speak("I'm listening...")
            print("🎤 Listening for your command...")
            recognizer.adjust_for_ambient_noise(source)
            audio = recognizer.listen(source, timeout=5) # Listen for up to 5 seconds
            command = recognizer.recognize_google(audio).lower()
            print("🗣️ You said:", command)
            speak(f"You said, {command}") # Echo command for confirmation

            # --- Command Logic for To-Do App Integration ---
            if "how are you" in command:
                speak("I'm doing great, thank you! How can I help you with your tasks today?")
            elif "your name" in command:
                speak("My name is SweetBot, your personal voice assistant.")
            elif "add task" in command:
                task_text_match = command.split("add task", 1)
                if len(task_text_match) > 1:
                    task_details = task_text_match[1].strip()
                    task_name = ""
                    task_time = ""

                    # Basic parsing for "add task X at Y time"
                    time_keywords = [" at ", " for ", " by "]
                    for keyword in time_keywords:
                        if keyword in task_details:
                            parts = task_details.split(keyword, 1)
                            task_name = parts[0].strip()
                            potential_time = parts[1].strip()

                            # Try to parse time, expecting HH:MM or simple AM/PM
                            try:
                                # Example: "5pm", "9am", "10:30"
                                if "pm" in potential_time and len(potential_time) > 2:
                                    hour = int(potential_time.replace("pm", "").strip())
                                    if 1 <= hour <= 11: hour += 12
                                    elif hour == 12: pass # 12 PM
                                    task_time = f"{hour:02d}:00"
                                elif "am" in potential_time and len(potential_time) > 2:
                                    hour = int(potential_time.replace("am", "").strip())
                                    if hour == 12: hour = 0 # 12 AM (midnight)
                                    task_time = f"{hour:02d}:00"
                                elif ":" in potential_time and len(potential_time) == 5:
                                    # Already HH:MM format
                                    task_time = potential_time
                                else:
                                    # Fallback for just a number, assume it's an hour, default to :00
                                    hour = int(potential_time)
                                    if 0 <= hour <= 23:
                                        task_time = f"{hour:02d}:00"

                            except ValueError:
                                task_time = "" # Invalid number or format for time

                            break # Stop after finding the first time keyword
                    else: # No time keyword found
                        task_name = task_details

                    if task_name:
                        await send_to_browser({"action": "addTask", "text": task_name, "time": task_time})
                        speak(f"Adding task: {task_name}. {'With reminder for ' + task_time if task_time else ''}")
                    else:
                        speak("I need a task to add. Please say 'add task' followed by the task.")
                else:
                    speak("What task would you like to add?")
            elif "mark task done" in command or "mark done" in command:
                task_text_match = command.replace("mark task done", "").replace("mark done", "").strip()
                if task_text_match:
                    await send_to_browser({"action": "markDone", "text": task_text_match})
                    speak(f"Attempting to mark {task_text_match} as done.")
                else:
                    speak("Which task should I mark as done?")
            elif "delete task" in command:
                task_text_match = command.split("delete task", 1)
                if len(task_text_match) > 1:
                    task_to_delete = task_text_match[1].strip()
                    if task_to_delete:
                        await send_to_browser({"action": "deleteTask", "text": task_to_delete})
                        speak(f"Attempting to delete task {task_to_delete}.")
                    else:
                        speak("Which task would you like to delete?")
                else:
                    speak("What task would you like to delete?")
            else:
                speak("Sorry, I didn't understand that command. Can you please repeat?")

        except sr.UnknownValueError:
            speak("Sorry, I couldn't understand what you said.")
        except sr.WaitTimeoutError:
            speak("I didn't hear anything. Please try again.")
        except sr.RequestError as e:
            speak(f"My speech service is currently unavailable. Please check your internet connection. Error: {e}")
        except Exception as e:
            print(f"An unexpected error occurred in respond_to_command: {e}")
            speak("An internal error occurred while processing your command.")

async def listen_for_wake_word():
    """Continuously listens for the wake word."""
    recognizer = sr.Recognizer()
    mic = sr.Microphone()

    with mic as source:
        recognizer.adjust_for_ambient_noise(source)
        print("👂 Waiting for wake word... Say 'Hey SweetBot'")

        while True:
            try:
                # If a command is being processed, briefly wait
                if recognizer_lock.locked():
                    await asyncio.sleep(0.1)
                    continue

                print("Waiting for audio input for wake word...")
                # Listen indefinitely but with a phrase time limit to avoid long silences
                audio = recognizer.listen(source, timeout=None, phrase_time_limit=3)
                phrase = recognizer.recognize_google(audio).lower()
                print("🔊 Heard:", phrase)

                if WAKE_WORD in phrase:
                    # Create a new task to respond to the command, so the main loop keeps listening
                    asyncio.create_task(respond_to_command(recognizer, source))

            except sr.UnknownValueError:
                pass  # Ignore unintelligible audio if no wake word was detected
            except sr.WaitTimeoutError:
                pass # No speech detected within phrase_time_limit, continue listening for wake word
            except sr.RequestError as e:
                speak(f"Could not request results from Google Speech Recognition service; {e}")
                await asyncio.sleep(5) # Wait before retrying after a network error
            except Exception as e:
                print(f"An unexpected error occurred in wake word listener: {e}")
                await asyncio.sleep(1) # Small delay to prevent tight loop on persistent errors

# --- Main entry point for the Python script ---
async def main():
    # Start the WebSocket server concurrently with the voice assistant
    websocket_server_task = websockets.serve(register_websocket, "localhost", 8765)
    voice_assistant_task = listen_for_wake_word()

    print("SweetBot Voice Assistant starting...")
    await asyncio.gather(websocket_server_task, voice_assistant_task)

if __name__ == "__main__":
    asyncio.run(main())