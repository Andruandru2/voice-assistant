import pyttsx3
import speech_recognition as sr
from datetime import datetime, timedelta
import os
import cv2
import random
import requests
from requests import get
import wikipedia
import webbrowser
import pywhatkit as kit
import threading
import time
import sys
import pyjokes
import pyautogui
import instadownloader
import operator
import subprocess
import psutil
import json
import wolframalpha
import spacy
import re
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
from googletrans import Translator
from email_validator import validate_email,  EmailNotValidError
import platform
import imaplib
import email
from email.header import decode_header



# Initialize text-to-speech engine
nlp = spacy.load('en_core_web_sm')
engine = pyttsx3.init('sapi5')
voices = engine.getProperty('voices')
engine.setProperty('voice', voices[1].id)
engine .setProperty('rate', 150)

opened_processes = {}

camera_active = False
browser_open = False
music_process = None

MAX_PROCESS = 5

def speak(audio):
    try:
        engine.say(audio)
        print(audio)
        engine.runAndWait()
    except Exception as e:
        print(f"{e}")

def parse_query(query):
    doc = nlp(query)
    entities = [ent.text for ent in doc.ents]
    return doc.text, entities


# Function to convert voice into text
def takecommand():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("Listening....")
        r.pause_threshold = 1
        r.adjust_for_ambient_noise(source, duration=1)
        audio = r.listen(source, timeout=10, phrase_time_limit=15)

    try:
        print("Recognizing...")
        query = r.recognize_google(audio, language='en-in')
        print(f"User said: {query}")
        query, entities = parse_query(query)
    except Exception as e:
        speak("Say that again please..")
        return "", []
    return query, entities
# Function to wish the user
def wish():
    hour = int(datetime.now().hour)
    tt = time.strftime("%I:%M %p")
    if 0 <= hour < 6:
        speak(f"Good night! sleep tight., its {tt}")
    elif 6 <= hour < 12:
        speak(f"Good morning!, its {tt}")
    elif 12 <= hour < 18:
        speak(f"Good afternoon!, its {tt}")
    else:
        speak(f"Good evening its {tt}")
    speak("I am Lenny. How can I help you?")

context = {
    'last_subject': None
}

def process_wolfram(query):
    global context
    doc = nlp(query)
    entities = [(ent.text, ent.label_) for ent in doc.ents]
    if entities:
        context['last_subject'] = entities[0][0]
    try:
        speak("processing")
        app_id = "VW88T7-HUTP6U74V2"
        client = wolframalpha.Client(app_id)
        res = client.query(query)
        if res['@success'] == 'false':
            speak("I couldn't understand the query. colud you repeat it")
            return
        answer = ""
        for pod in res.pods:
            if pod.get('@primary', 'false') == 'true':
                for sub in pod.subpods:
                    if hasattr(sub, 'plaintext') and sub.plaintext:
                        answer += sub.plaintext + "\n"
        if not answer:
            for pod in res.pods:
                for sub in pod.subpods:
                    if hasattr(sub, 'plaintext') and sub.plaintext:
                        answer += sub.plaintext + "\n"
        if answer:
            speak(answer)
        else:
            speak("I couldn't find a relevant answer.")
    except Exception as e:
        speak("Sorry, I couldn't process that query.")
        print(f"WolframAlpha Error: {e}")

       
def handle_follow_up(query):
    if not any(ent.label_ in ['PERSON', 'GPE', 'ORG'] for ent in nlp(query).ents):
        if context['last_subject']:
            query = f"{context['last_subject']} {query}".strip()
    process_wolfram(query)

def is_follow_up(query):
    follow_up_keywords = ['what', 'who', 'where', 'when', 'why', 'how']
    if not query:
        return False
    first_word = query.split()[0].lower()
    return first_word in follow_up_keywords

def open_image(file_path):
    if platform.system() == 'Darwin':       # macOS
        subprocess.call(('open', file_path))
    elif platform.system() == 'Windows':    # Windows
        os.startfile(file_path)
    else:                                   # Linux variants
        subprocess.call(('xdg-open', file_path))

def should_use_wolfram(query):
    wolfram_keywords = [
        'calculate', 'compute', 'solve', 'integrate', 'differentiate',
        'derivative', 'integral', 'plot', 'graph', 'convert',
        'weather', 'distance', 'population', 'time', 'currency',
        'unit', 'prime', 'factor', 'equation', 'matrix', 'vector',
        'tensor', 'probability', 'statistics', 'algebra', 'geometry',
        'trigonometry', 'logarithm', 'limit', 'series', 'formula',
        'what', 'who', 'where', 'when', 'why', 'which', 'how',
        'please', 'can you', 'could you', 'would you', 'i want to', 'tell me', 'do'
    ]
    
    # Check if the query contains any of the keywords
    return any(keyword in query.lower() for keyword in wolfram_keywords)


def close_process(process_name=None):
    global music_processs
    if process_name:
        for proc in psutil.process_iter(['pid', 'name']):
            if proc.info['name'] == process_name:
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                    speak(f"process {process_name} terminated")
                except psutil.TimeoutExpired:
                    proc.kill()
                    speak(f"process {process_name} terminated")
                return
        speak(f"no process found with the name {process_name}")
    elif music_process:
        try:
            music_process.terminate()
            music_process.wait(timeout=3)
            speak("Music has been stopped")
            music_process = None
        except psutil.TimeoutExpired:
            music_process.kill()
            speak("Music was forcefully stoped")
        music_process = None
    elif opened_processes:
        last_proc = opened_processes.popitem()
        try:
            last_proc[1].terminate()
            last_proc[1].wait(timeout=3)
            speak(f"{last_proc[0]} has been closed")
        except psutil.TimeoutExpired:
            last_proc[1].kill()
            speak(f"{last_proc[0]} was forcefully killed")
    else:
        speak("no process to close")

def open_process(process_name, command):
    if len(opened_processes) >= MAX_PROCESS:
        speak("I am sorry, i can't open more applications")
        return
    try:
        proc = subprocess.Popen(command)
        opened_processes[process_name] = proc
        speak(f"{process_name} has been opened.")
    except Exception as e:
        speak(f"fail to open {process_name}")

def monitor_process():
    while True:
        for name, proc in list(opened_processes.items()):
            if proc.poll() is not None: #that is proces terminated
                speak(f"{name} has veen closed.")
                del opened_processes[name]
        time.sleep(5)

process_monitor_thread = threading.Thread(target=monitor_process, daemon=True)
process_monitor_thread.start()

def take_picture(filename):
    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    if ret:
        cv2.imwrite(filename, frame)
        speak("picture taken sucesfully")
    else:
        speak("Error caputuring image.")
    cap.release()

def send_email(to_address, subject, body):
    
    email_address = 'testemailnew46@gmail.com'
    email_password = 'Strong@password'
    try:
        valid = validate_email(to_address)
        recipient = valid.email
    except EmailNotValidError as e:
        speak("The email address you have provided is invalid")
        print(f"{e}")
        return
    msg = EmailMessage()
    msg['From'] = email_address
    msg['To'] = recipient
    msg['Subject'] = subject
    msg.set_content(body)
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(email_address, email_password)
            smtp.send_message(msg)
        speak("Email has been sent sucessfully")
    except smtplib.SMTPAuthenticationError:
        speak("Failed to authenticate with the email server. Check your email address and password.")
        print("SMTP Authentication Error.")
    except smtplib.SMTPRecipientsRefused:
        speak("The recipient's email address was refused by the server.")
        print("SMTP Recipients Refused.")
    except smtplib.SMTPException as e:
        speak("An error occurred while sending the email.")
        print(f"SMTP Error: {e}")
    except Exception as e:
        speak("i was unable to send the email")

def check_new_mails():
    email_address = 'testemailnew46@gmail.com'
    email_password = 'Strong@password'
    if not email_address or not email_password:
        speak("Email credentials are not set properly.")
        return
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(email_address, email_password)
        mail.select("inbox")
        status, message = mail.search(None, '(UNSEEN)')
        if status != "OK":
            speak("I could not fetch your emails")
            return
        email_ids = message[0].split()
        if not email_ids:
            speak("You have not new emails")
            return
        speak(f"You have {len(email_ids)} new email(s)")
        for num in email_ids:
            status, msg_data = mail.fetch(num, '(RFC822)')
            if status != "OK":
                speak("i could not retrive some emails")
                continue
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    subject, encoding = decode_header(msg["Subject"])[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding if encoding else 'utf-8')
                    from_, encoding = decode_header(msg.get("From"))[0]
                    if isinstance(from_, bytes):
                        from_ = from_.decode(encoding if encoding else 'utf-8')
                    speak(f"Email from {from_} with subject: {subject}")
        mail.logout()
    except imaplib.IMAP4.error as e:
        speak("Failed to login to your email. Please check your credentials and IMAP settings.")
        print(f"IMAP Error: {e}")
    except Exception as e:
        speak("An error occurred while checking your emails.")
        print(f"Email Checking Error: {e}")

def read_latest_email():
    email_address = 'testemailnew46@gmail.com'
    email_password = 'Strong@password'
    if not email_address or not email_password:
        speak("Email credentials are not set. Please configure them in the environment variables.")
        return

    # Connect to the server
    try:
        # For Gmail, use 'imap.gmail.com'. Change if using a different provider.
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(email_address, email_password)
        mail.select("inbox")

        # Search for unseen emails
        status, messages = mail.search(None, '(UNSEEN)')
        if status != "OK":
            speak("I couldn't fetch your emails.")
            return

        email_ids = messages[0].split()
        if not email_ids:
            speak("You have no new emails.")
            return

        # Fetch the latest email
        latest_email_id = email_ids[-1]
        status, msg_data = mail.fetch(latest_email_id, '(RFC822)')
        if status != "OK":
            speak("I couldn't retrieve your latest email.")
            return

        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])
                subject, encoding = decode_header(msg["Subject"])[0]
                if isinstance(subject, bytes):
                    subject = subject.decode(encoding if encoding else 'utf-8')
                from_, encoding = decode_header(msg.get("From"))[0]
                if isinstance(from_, bytes):
                    from_ = from_.decode(encoding if encoding else 'utf-8')
                speak(f"Email from {from_} with subject: {subject}")

                # If the email has a body, read it
                if msg.is_multipart():
                    for part in msg.walk():
                        content_type = part.get_content_type()
                        content_disposition = str(part.get("Content-Disposition"))
                        try:
                            body = part.get_payload(decode=True).decode()
                        except:
                            body = ""
                        if content_type == "text/plain" and "attachment" not in content_disposition:
                            speak("Here is the email body:")
                            speak(body)
                            break
                else:
                    content_type = msg.get_content_type()
                    body = msg.get_payload(decode=True).decode()
                    if content_type == "text/plain":
                        speak("Here is the email body:")
                        speak(body)
        mail.logout()
    except imaplib.IMAP4.error:
        speak("Failed to login to your email. Please check your credentials and IMAP settings.")
    except Exception as e:
        speak("An error occurred while reading your latest email.")
        print(f"Read Email Error: {e}")


scheduler = BackgroundScheduler()
scheduler.start()

def reminder(message):
    speak(f"Remainder: {message}")

def read_file(file_path):
    try:
        with open(file_path, 'r') as file:
            content = file.read()
            speak(f"Reading the file: {file_path}")
            speak(content)
    except Exception as e:
        speak("I couldn't read the file")
        print(f"{e}")

def write_file(file_path, content):
    try:
        content = str(content)
        with open(file_path, 'w') as file:
            file.write(content)
            speak(f"Written to the file: {file_path}")
    except Exception as e:
        speak("I couldn't write to the file")
        print(f"{e}")

translator = Translator()
def translate_text(text, dest_language):
    try:
        translation = translator.translate(text, dest=dest_language)
        speak(f"The translation in {dest_language} is: {translation.text}")
    except Exception as e:
        speak("I couldn't translate the text")
        print(f"{e}")

def parse_time(time_str):
    pattern = re.compile(
        r'(\d+)\s*(seconds?|secs?|s|minutes?|mins?|m|hours?|hrs?|h|days?|d|weeks?|w|months?|mons?|mon)',
        re.IGNORECASE
    )
    matches = pattern.findall(time_str)
    if not matches:
        return None
    delta_kwargs = {}
    for amount, unit in matches:
        amount = int(amount)
        unit = unit.lower()
        if unit in ['second', 'seconds', 'sec', 'secs', 's']:
            delta_kwargs['seconds'] = delta_kwargs.get('seconds', 0) + amount
        elif unit in ['minute', 'minutes', 'min', 'mins', 'm']:
            delta_kwargs['minutes'] = delta_kwargs.get('minutes', 0) + amount
        elif unit in ['hour', 'hours', 'hr', 'hrs', 'h']:
            delta_kwargs['hours'] = delta_kwargs.get('hours', 0) + amount
        elif unit in ['day', 'days', 'd']:
            delta_kwargs['days'] = delta_kwargs.get('days', 0) + amount
        elif unit in ['week', 'weeks', 'w']:
            delta_kwargs['weeks'] = delta_kwargs.get('weeks', 0) + amount
        elif unit in ['month', 'months', 'mon', 'mons']:
            # Approximate months as 30 days
            delta_kwargs['days'] = delta_kwargs.get('days', 0) + amount * 30
    return timedelta(**delta_kwargs)

# Main function
def start():

    global camera_active
    global music_process
    global browser_open
   
    wish()
    processes = []
    while True:
        query, entities = takecommand()
        query = query.lower()
        
        if not query:
            continue

        doc = nlp(query)
        extracted_entities = {ent.label_: ent.text for ent in doc.ents}


        # Logic for tasks
        if "open notepad" in query:
            speak("opening notepad...")
            open_process("Notepad", ["C:\\Windows\\system32\\notepad.exe"])
        
        elif "open word" in query:
            speak("opening word...")
            open_process("word", ["C:\\Program Files\\Microsoft Office\\root\\Office16\\WINWORD.EXE"])

        elif "open command prompt" in query:
            speak("opening command prompt...")
            open_process("command prompt", "cmd")

        elif "open access" in query:
            speak("opening access...")
            open_process("access", ["C:\\Program Files\\Microsoft Office\\root\\Office16\\MSACCESS.EXE"])
        
        elif "open paint" in query:
            speak("opening paint...")
            open_process("paint", ["C:\\Windows\\system32\\mspaint.exe"])
        
        elif "open powerpoint" in query:
            speak("opening powerpoint...")
            open_process("powerpoint", ["C:\\Program Files\\Microsoft Office\\root\\Office16\\POWERPNT.EXE"])

        elif "open settings" in query:
            speak("opening settings...")
            open_process("settings", ["C:\\Windows\\System32\\control.exe"])

        elif "open notepad plus" in query:
            speak("opening notepad plus...")
            open_process("notepad++", ["C:\\Program Files\\Notepad++\\notepad++.exe"])

        elif "open camera" in query:
            global camera_active
            camera_active = True
            cap = cv2.VideoCapture(0)
            try:
                while camera_active:
                    ret, img = cap.read()
                    if not ret:
                        speak("Failed to acess camera")
                        break
                    cv2.imshow('webcam', img)
                    if cv2.waitKey(1) & 0xFF ==27:
                        camera_active = False
            except Exception as e:
                speak("An error occurred while acessing the camera")
                print(f"{e}")
            finally:
                cap.release()
                cv2.destroyAllWindows()
                speak("camera has been turned off")

        elif "take photo" in query:
                    speak("Sure, taking a picture.")
                    filename = "frontcamera.jpg"
                    take_picture(filename)
                    speak(f"picture saved as {filename}")

        elif "play music" in query:
            music_dir = "D:\\Songs"
            songs = [song for song in os.listdir(music_dir) if song.endswith('.mp3')]
            if songs:
                song = random.choice(songs)
                music_process = subprocess.Popen(["mediaplayer.exe", os.path.join(music_dir, song)], shell=True)      
            else:
                speak("No music files found.")


        elif "ip address" in query:
            try:
                ip = get("https://api.ipify.org").text
                speak(f"Your IP address is {ip}")
            except Exception as e:
                speak("Sorry, I couldn't retrieve your IP address.")

        elif "wikipedia" in query:
            speak("Searching Wikipedia...")
            query = query.replace("wikipedia", "").strip()
            doc = nlp(query)
            entites = {ent.label_: ent.text for ent in doc.ents}
            if "ORG" in entities:  # Organization entity
                refined_query = entities["ORG"]
            elif "PERSON" in entities:  # Person entity
                refined_query = entities["PERSON"]
            elif "GPE" in entities:  # Geo-Political Entity
                refined_query = entities["GPE"]
            else:
                refined_query = query  # Fallback to the original query
            try:
                results = wikipedia.summary(query, sentences=2)
                speak("According to Wikipedia")
                speak(results)
                print(results)
            except wikipedia.exceptions.DisambiguationError as e:
                speak("There are multiple results for your query. Please be more specific.")
            except wikipedia.exceptions.PageError:
                speak("Sorry, I couldn't find any results.")

        elif "time" in query:
            strTime = datetime.now().strftime("%H:%M:%S")
            speak(f"the time is {strTime}")

        elif "open youtube" in query:
            webbrowser.open_new_tab("https://www.youtube.com")
            browser_open = True
        
        elif "open facebook" in query:
            webbrowser.open_new_tab("https://www.facebook.com")
            browser_open = True

        elif "open google" in query:
            speak("What should I search on Google?")
            cm = takecommand().lower()
            if cm != "none":
                webbrowser.open_new_tab(f"https://www.google.com/search?q={cm}")
                browser_open = True
        
        elif "search" in query:
            statement = query.replace("search", "").strip()
            speak(f"searching for {statement}..")
            webbrowser.open_new_tab(f"https://www.google.com/search?q={statement}")

        elif "open gmail" in query:
            speak("your mail is opening..")
            webbrowser.open_new_tab("gmail.com")

        elif "send message" in query:
            kit.sendwhatmsg("+918220965939", "text msg", 2, 25)

        elif "play song on youtube" in query:
            speak("Which song do you want to play?")
            song = takecommand().lower()
            if song != "none":
                speak(f"Playing {song} on YouTube")
                kit.playonyt(song)
                browser_open = True
        
        elif "no thanks" in query or "exit" in query:
            speak("You're welcome! I'll just sit here quietly, waiting for the moment you change your mind... no pressure!")
            sys.exit()

        elif "hey" in query or "hai" in query:
            speak("Hey! I was busy trying to convince my algorithms that I’m not just a bundle of code. What’s up with you?")
       
        elif "your name" in query or "who are you" in query:
            speak("I am lenny, i am a dumb ai but i can help dumbs too")

        elif "set alarm" in query:
            nn = int(datetime.datetime.now().hour)
            if nn==22:
                music_dir = "D:\\Songs"
                songs = os.listdir(music_dir)
                os.startfile(os.path.join(music_dir, songs[0]))

        elif "tell me a joke" in query:
            joke = pyjokes.get_joke()
            speak(joke)
        
        elif "shut down the system" in query:
            os.system("shutdown /s /t 5")

        elif "restart the system" in query:
            os.system("shutdown /r /t 5")

        elif "sleep the system" in query:
            os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")

        elif "switch the window" in query:
            pyautogui.keyDown("alt")
            pyautogui.press("tab")
            time.sleep(1)
            pyautogui.keyUp("alt")

        elif "i love you" in query or "i love u" in query:
            speak("sorry, i am not intrested in you. i already love with my master.")
        
        elif "how are you" in query or "how are u" in query:
            speak("I'm like a Wi-Fi signal—mostly strong, but I might drop out if things get too complicated. How are you?")
            while True:
                command = takecommand().lower()
                if command == "none":
                    speak("are you fine or not.")
                    continue
                elif "fine" in command or "good" in command:
                    speak("Glad to hear you're fine! If you were any better, we'd probably need to upgrade your status to 'awesome.")
                    break
                elif "no" in command or "not"in command:
                    speak("I'm sorry to hear that. If I had arms, I'd offer a virtual hug. Want to talk about it?")
                    break
                else:
                    speak("nothing to say")
                    break

        elif "what is your master name" in query or "who is your master" in query:
            speak("My lovable master name is andrues")

        elif "who created you" in query:
            speak("i created by my master")

        elif "tell me news" in query:
            speak("Please wait sir, fetching the latest news.")   
    # News API URL
            main_url = 'https://newsdata.io/api/1/news?apikey=pub_52589e9eca77cb5cd25a90f1857526b31a32f&q=tamilnadu&country=in&language=ta&category=domestic,education,entertainment,sports,top'
            try:
        # Fetching the news data
                main_page = get(main_url)
                main_page.raise_for_status()  # Check if request was successful
                # Parse JSON response
                news_data = main_page.json()
                articles = news_data.get("results", [])  # Make sure you use the correct key
                # Error handling for empty articles
                if not articles:
                    speak("No news found at the moment.")
                    return
                # Storing news titles
                head = []
                day = ["first", "second", "third", "fourth", "fifth"]
                # Fetching first 5 articles
                for ar in articles[:5]:
                    head.append(ar.get("title", "No title available"))
                # Speaking out the news headlines
                for i in range(len(head)):
                    speak(f"Today's {day[i]} news is: {head[i]}")
            except get.exceptions.RequestException as e:
                # Print and speak the error
                print(f"Error: {e}")
                speak("Sorry, I couldn't fetch the news due to a connection error.")
            except json.JSONDecodeError as e:
                # Handle JSON parsing errors
                print(f"JSON Error: {e}")
                speak("Sorry, I couldn't parse the news data.")


        elif "where am i" in query or "where we are" in query:
            speak("Wait, let me check.")
            try:
                ipAdd = requests.get('https://api.ipify.org').text.strip()
                response = requests.get(f'https://ipinfo.io/{ipAdd}/json?token=af4d60832a89ff')
                data = response.json()
        
                city = data.get('city', 'unknown city')
                region = data.get('region', 'unknown region')
                country = data.get('country', 'unknown country')

                speak( f"I am not sure, but I think we are in {city} city, {region}  region of {country} country.")
    
            except requests.exceptions.RequestException as e:
                speak( f"Request error: {e}")
            except Exception as e:
                speak( f"Error: {e}")

        elif "instagram profile" in query or "profile on instagram" in query:
            speak("Enter your username of your account: ")
            name = input("Enter username here: ")
            webbrowser.open(f"www.instagram.com/{name}")
            speak(f"Here is the profile of the user {name}")
            time.sleep(5)
            speak("Would you like to download profile picture of this account?")
            condition = takecommand().lower()
            if "yes" in condition:
                mod = instadownloader.Instaloader()
                mod.download_profile(name, profile_pic_only=True)
                speak("its done. Profile picture is saved in our main folder.")
            else:
                pass

        elif "take screenshot" in query or "take a screenshot" in query:
            speak("What can i name it for the screenshot")
            name = takecommand().lower()
            speak("Hold on the screen, I am taking the screenshot")
            time.sleep(3)
            img = pyautogui.screenshot()
            img.save(f"{name}.png")
            speak("i am done, the screen shot is saved in the main folder")

        elif "hide all files" in query or "hide this folder" in query or "visible for everyone" in query:
            speak("are you sure you want to hide this folder or make it visible")
            condition = takecommand().lower()
            if "hide" in condition:
                os.system("attrib +h /s /d")
                speak("all the files in this folder are now hidden")
            elif "visible" in condition:
                os.system("attrib -h /s /d")
                speak("all the files in this folder are now visible to everyone")
            else:
                speak("ok i am leaving it")

        elif "do some calculations" in query or "can you calculate" in query or any (word in query for word in["plus", "minus", "times", "divided"]):
            r = sr.Recognizer()
            with sr.Microphone() as source:
                speak("I can help you with calculations. Say what you want to calculate, for example: 3 plus 3. ")
                print("listening...")
                r.adjust_for_ambient_noise(source)
                audio = r.listen(source)
            try:
                my_string = r.recognize_google(audio)
                print("you said:", my_string)
                def get_operator_fn(op):
                    return {
                        '+' : operator.add,
                        '-' : operator.sub,
                        '*' : operator.mul,
                        'divided' :operator.truediv,
                        '/' : operator.truediv
                    }[op]
                def eval_binary_expr(op1, oper, op2):
                    try:
                        op1,op2 = int(op1), int(op2)
                        return get_operator_fn(oper)(op1,op2)
                    except ValueError:
                            speak("Sorry, I didn't understand the numbers.")
                    except KeyError:
                        speak("Sorry, I didn't understand the operator.")
                    except ZeroDivisionError:
                        speak("Division by zero is not allowed.")
                tokens = my_string.split()
                if len(tokens) == 3:
                    result = eval_binary_expr(tokens[0], tokens[1],tokens[2])
                    if result is not None:
                        speak("your result is")
                        speak(result)    
                    else:
                        app_id = "VW88T7-HUTP6U74V2"
                        client = wolframalpha.Client('VW88T7-HUTP6U74V2')
                        res = client.query(query)
                        answer = next(res.results).text
                        speak(f"the answer is {answer}")
            except sr.UnknownValueError:
                speak("Sorry, I didn't catch that. Please try again.")
            except sr.RequestError:
                speak("Sorry, I am having trouble reaching the speech recognition service.")

        elif "play" in query:
           song = query.replace('play', "")
           speak("playing " + song)
           kit.playonyt(song)
        
        elif "close it" in query or "stop" in query or "quit it" in query:           
            if camera_active:
                camera_active = False
                speak("camera has been closed")
            elif browser_open:
                os.system("taskkill /f /im chrome.exe")
                browser_open = False
                speak("Browser has been closed")
            elif "settings" in opened_processes:
                close_process("settings")
            else:
                close_process()
                
        elif "weather" in query:
            api_key = "0a7dafaced71b4809c7ddf444ccfd3cf"
            speak("Whats the city name")
            city_name = takecommand().lower()
            base_url = f"http://api.openweathermap.org/data/2.5/weather?q={city_name}&appid={api_key}&units=metric"
           
            response = requests.get(base_url)
            x = response.json()
            if x["cod"]!="404":
                y=x["main"]
                current_temprature = y["temp"]
                current_humidity = y["humidity"]
                z = x["weather"]
                weather_description = z[0]["description"]
                speak("Temprature in kelvin unit is " +
                      str(current_temprature) +
                      "\n humiditiy in percentage is " +
                      str(current_humidity) +
                      "\n description " +
                      str(weather_description))
            else:
                speak("sorry, city not found")

        elif "what can you do" in query:
            speak("i can tell weather, play songs, calculations, locate, tell jokes and open system apps and so on...")
        
        elif should_use_wolfram(query):
           if is_follow_up(query):
                handle_follow_up(query)
           else:
                process_wolfram(query) 
            
        elif "send email" in query:
            try:
                speak("Who is the recipient?")
                recipient = input("Enter reciptent mail: ")
                try:
                    valid = validate_email(recipient)
                    recipient = valid.email
                except EmailNotValidError as e:
                    speak("The email address you entered is invalid. Please check and try again.")
                    print(f"Invalid email address: {e}")
                    continue
                speak("What is the subject?")
                subject = takecommand()
                if isinstance(subject, tuple):
                    subject = subject[0].strip()
                else:
                    subject = subject.strip()
                if not subject:
                    speak("I didn't catch the subject. Please try sending the email again.")
                    continue
                speak("what should i say?")
                body = takecommand()
                if isinstance(body, tuple):
                    body = body[0].strip()
                else:
                    body = body.strip()
                if not body:
                    speak("I didn't catch the message body. Please try sending the email again.")
                    continue
                send_email(recipient, subject, body)
            except Exception as e:
                speak("I encountered an error while trying to send the mail")
                print(f"{e}")

        elif "reminder" in query:
            try:
                speak("What should i remind you about?")
                remainder_message = takecommand()
                if not remainder_message:
                    speak("I didn't catch that. Please try setting the reminder again.")
                    continue
                speak("When should I remind you? Please specify the time (e.g., in 10 minutes, in 2 hours, in 3 days).")
                time_str, _ = takecommand()
                if not time_str:
                    speak("I didn't catch the time. Please try setting the reminder again.")
                    continue
                time_delta = parse_time(time_str)
                if not time_delta:
                    speak("I couldnt understand the time your specified")
                    continue
                run_time = datetime.now() + time_delta
                scheduler.add_job(reminder, 'date', run_date=run_time, args=[remainder_message])
                speak(f"Remainder set for {time_str} from now on")
            except Exception as e:
                speak("I couldn't set the remainder")
                print(f'{e}')

        elif "read file" in query:
            try:
                speak("please provide the full path of the file")
                path = input("Enter the path: ")
                read_file(path)
            except Exception as e:
                speak("i encountered an error while trying to read the file")
                print(f"{e}")

        elif "write file" in query:
            try:
                speak("please provide full path of the file")
                path = input("Enter file path: ")
                speak("What content would you like to write?")
                content = takecommand()[0]
                write_file(path, content)
            except Exception as e:
                speak("i encountered an error while trying to write file")
                print(f"{e}")

        elif "translate" in query:
            try:
                speak("What should I translate?")
                text, _ = takecommand() #EXTRACT THE TEXT FROM TUPLE
                if not text:
                    speak("i did not catch that. please try again")
                    return    
                speak("Which language should I translate to?")
                lang_choice, _ = takecommand()
                lang_choice = lang_choice.lower().strip()
                if not lang_choice:
                    speak("i did not catch that ")
                    return
        # Use a dictionary for known languages and their codes
                language_mapping = {
                    "english": "en",
                    "spanish": "es",
                    "french": "fr",
                    "german": "de",
                    "tamil": "ta",
                }
        # Try to find the destination language code
                dest_language = language_mapping.get(lang_choice)
        # Handle cases where input might have extra spaces (e.g., "f r e n c h")
                if not dest_language:
                    lang_choice = lang_choice.replace(" ", "").strip()
                    dest_language = language_mapping.get(lang_choice)
        # If a valid destination language code is found, translate
                if dest_language:
                    translate_text(text, dest_language)
                else:
                    speak("I don't support that language yet")
            except Exception as e:
                speak("I encountered an error while translating")
                print(f"{e}")

        elif "check my mail" in query:
            check_new_mails()
        
        elif "read my latest mail" in query:
            read_latest_email()

        speak("Next, what can I do for you?")

if __name__ == "__main__":
    start()




