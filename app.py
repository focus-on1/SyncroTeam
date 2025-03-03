# api/index.py (principal point d'entrée pour Vercel)
from flask import Flask, send_from_directory, request
import os

app = Flask(__name__)

@app.route('/', methods=['GET'])
def home():
    return "Bienvenue sur le serveur de calendrier !"

@app.route('/calendar.ics', methods=['GET'])
def serve_calendar():
    return send_from_directory('static', 'event.ics')