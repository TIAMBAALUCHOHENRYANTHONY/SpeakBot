import openai
import speech_recognition as sr
import pyttsx3
import os
import threading
from queue import Queue
from flask import Flask, request, jsonify, render_template, session
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

app = Flask(__name__)
app.secret_key = "supersecretkey"

# Initialize the OpenAI API
openai.api_key = os.getenv("OPENAI_API_KEY")

# Initialize the text-to-speech engine
engine = pyttsx3.init()
engine.setProperty('voice', 'english')
speech_queue = Queue()

def speech_worker():
    while True:
        texto = speech_queue.get()
        if texto is None:
            break
        print(f"Reproduciendo: {texto}")
        engine.say(texto)
        engine.runAndWait()
        speech_queue.task_done()

speech_thread = threading.Thread(target=speech_worker, daemon=True)
speech_thread.start()

def transcribir_audio_a_texto(filename):
    recognizer = sr.Recognizer()
    with sr.AudioFile(filename) as source:
        audio = recognizer.record(source)
    try:
        return recognizer.recognize_google(audio, language="en-US")
    except sr.UnknownValueError:
        print("Could not understand the audio")
        return ""
    except sr.RequestError as e:
        print(f"Could not request results; {e}")
        return ""

def generar_respuesta(prompt, theme):
    contextos = {
        "likes_and_dislikes": "Talk about likes and dislikes.",
        "family_and_friends": "Talk about family and friends.",
        "school_and_work": "Talk about school and work.",
        "holiday_and_travel": "Talk about holidays and travel.",
        "compare_and_contrast": "Compare and contrast different situations.",
        "advantages_and_disadvantages": "Discuss advantages and disadvantages of things and situations.",
        "environment_problems": "Talk about environmental problems."
    }
    contexto = contextos.get(theme, "You are a helpful assistant.")

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": contexto},
            {"role": "user", "content": prompt}
        ],
        max_tokens=4000,
        n=1,
        stop=None,
        temperature=0.5,
    )
    return response["choices"][0]["message"]["content"]

def generar_pregunta_inicial(theme):
    preguntas = {
        "likes_and_dislikes": "What are some of your likes and dislikes?",
        "family_and_friends": "Can you tell me about your family and friends?",
        "school_and_work": "What do you do at school or work?",
        "holiday_and_travel": "Where do you like to go on holiday?",
        "compare_and_contrast": "Can you compare and contrast these situations?",
        "advantages_and_disadvantages": "What are the advantages and disadvantages of this?",
        "environment_problems": "What do you think about environmental problems?"
    }
    return preguntas.get(theme, "What would you like to talk about today?")

def hablar_texto(texto):
    print(f"Queueing speech: {texto}")
    speech_queue.put(texto)

@app.route("/")
def index():
    saludo = "Welcome to the chat application"
    hablar_texto(saludo)
    return render_template("index.html")

@app.route("/transcribir", methods=["POST"])
def transcribir():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400
    filepath = os.path.join("uploads", file.filename)
    file.save(filepath)
    texto = transcribir_audio_a_texto(filepath)
    os.remove(filepath)
    return jsonify({"texto": texto})

@app.route("/responder", methods=["POST"])
def responder():
    data = request.json
    prompt = data.get("prompt", "")
    theme = session.get("theme", "general")
    respuesta = generar_respuesta(prompt, theme)
    hablar_texto(respuesta)
    return jsonify({"respuesta": respuesta})

@app.route("/pregunta_inicial", methods=["POST"])
def pregunta_inicial():
    data = request.json
    theme = data.get("theme", "general")
    session["theme"] = theme
    pregunta = generar_pregunta_inicial(theme)
    hablar_texto(pregunta)
    return jsonify({"pregunta": pregunta})

@app.route("/hablar", methods=["GET"])
def hablar():
    mensaje = request.args.get("mensaje", "No message received")
    hablar_texto(mensaje)
    return jsonify({"mensaje": mensaje})

if __name__ == "__main__":
    if not os.path.exists("uploads"):
        os.makedirs("uploads")
    app.run(debug=True, port=9000)  # Aquí especificamos el puerto 5001

