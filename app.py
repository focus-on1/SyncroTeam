from flask import Flask, send_from_directory
import os

app = Flask(__name__)

@app.route('/')
def index():
    return "Bienvenue sur le serveur de calendrier !"

@app.route('/calendar.ics')
def calendar():
    # Remplacez le chemin ci-dessous par celui de votre fichier .ics dans le répertoire static
    return send_from_directory(os.path.join(app.root_path, 'static'), 'event.ics')

if __name__ == "__main__":
    # Lancer l'app Flask sur 0.0.0.0 pour écouter sur toutes les interfaces
    app.run(host='0.0.0.0', port=5000, debug=True)
