# app.py
from flask import Flask, send_from_directory
import os

app = Flask(__name__)

@app.route('/')
def index():
    return "Bienvenue sur le serveur de calendrier !"

@app.route('/calendar.ics')
def calendar():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'event.ics')

# Point d'entrée pour Vercel
from flask import request

@app.route('/api/index', methods=['GET'])
def api_index():
    return index()

@app.route('/api/calendar', methods=['GET'])
def api_calendar():
    return calendar()

app = app