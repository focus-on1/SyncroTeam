from flask import Flask, request, Response
import os
import icalendar
import vobject
import time
from datetime import datetime

app = Flask(__name__)

# Chemin vers votre fichier ICS
ICS_FILE_PATH = "calendrier.ics"
STORAGE_PATH = "./calendars"

# Structure pour stocker les calendriers et événements
calendars = {}

def create_default_calendar():
    """Crée un calendrier ICS par défaut s'il n'existe pas"""
    if not os.path.exists(ICS_FILE_PATH):
        cal = icalendar.Calendar()
        cal.add('prodid', '-//MonCalDAV Local//FR')
        cal.add('version', '2.0')
        
        # Ajouter un événement exemple
        event = icalendar.Event()
        event.add('summary', 'Événement test')
        event.add('dtstart', datetime.now())
        event.add('dtend', datetime.now())
        event.add('dtstamp', datetime.now())
        event.add('uid', f'test-event-{int(time.time())}@local')
        
        cal.add_component(event)
        
        with open(ICS_FILE_PATH, 'wb') as f:
            f.write(cal.to_ical())
            
    # Créer le dossier de stockage
    os.makedirs(STORAGE_PATH, exist_ok=True)

def load_ics_file():
    """Charge le fichier ICS en mémoire"""
    with open(ICS_FILE_PATH, 'rb') as f:
        cal_data = f.read()
    
    # Mettre à jour le stockage mémoire
    calendars['default'] = cal_data
    
    # Copier vers le stockage CalDAV
    user_path = os.path.join(STORAGE_PATH, "user")
    os.makedirs(user_path, exist_ok=True)
    
    with open(os.path.join(user_path, "calendar.ics"), 'wb') as f:
        f.write(cal_data)

def save_calendar(cal_data, uid="default"):
    """Sauvegarde les données du calendrier dans le fichier ICS"""
    # Mettre à jour le stockage mémoire
    calendars[uid] = cal_data
    
    # Sauvegarder dans le fichier ICS
    with open(ICS_FILE_PATH, 'wb') as f:
        f.write(cal_data)

# Routes CalDAV essentielles

@app.route('/.well-known/caldav', methods=['GET'])
def caldav_discovery():
    """Point de découverte pour les clients CalDAV"""
    return Response('', status=301, headers={'Location': '/calendars/'})

@app.route('/calendars/', methods=['PROPFIND'])
def propfind_calendars():
    """Répond aux requêtes PROPFIND pour la découverte des calendriers"""
    xml_response = f"""<?xml version="1.0" encoding="utf-8"?>
<D:multistatus xmlns:D="DAV:" xmlns:C="urn:ietf:params:xml:ns:caldav">
  <D:response>
    <D:href>/calendars/</D:href>
    <D:propstat>
      <D:prop>
        <D:resourcetype>
          <D:collection/>
        </D:resourcetype>
        <D:displayname>Calendriers</D:displayname>
      </D:prop>
      <D:status>HTTP/1.1 200 OK</D:status>
    </D:propstat>
  </D:response>
  <D:response>
    <D:href>/calendars/user/</D:href>
    <D:propstat>
      <D:prop>
        <D:resourcetype>
          <D:collection/>
        </D:resourcetype>
        <D:displayname>Utilisateur</D:displayname>
      </D:prop>
      <D:status>HTTP/1.1 200 OK</D:status>
    </D:propstat>
  </D:response>
</D:multistatus>"""
    
    return Response(xml_response, status=207, mimetype='application/xml')

@app.route('/calendars/user/', methods=['PROPFIND'])
def propfind_user_calendars():
    """Répond aux requêtes PROPFIND pour les calendriers de l'utilisateur"""
    xml_response = f"""<?xml version="1.0" encoding="utf-8"?>
<D:multistatus xmlns:D="DAV:" xmlns:C="urn:ietf:params:xml:ns:caldav">
  <D:response>
    <D:href>/calendars/user/</D:href>
    <D:propstat>
      <D:prop>
        <D:resourcetype>
          <D:collection/>
        </D:resourcetype>
        <D:displayname>Utilisateur</D:displayname>
      </D:prop>
      <D:status>HTTP/1.1 200 OK</D:status>
    </D:propstat>
  </D:response>
  <D:response>
    <D:href>/calendars/user/calendar.ics</D:href>
    <D:propstat>
      <D:prop>
        <D:resourcetype>
          <D:collection/>
          <C:calendar/>
        </D:resourcetype>
        <D:displayname>Mon Calendrier</D:displayname>
        <C:supported-calendar-component-set>
          <C:comp name="VEVENT"/>
        </C:supported-calendar-component-set>
      </D:prop>
      <D:status>HTTP/1.1 200 OK</D:status>
    </D:propstat>
  </D:response>
</D:multistatus>"""
    
    return Response(xml_response, status=207, mimetype='application/xml')

@app.route('/calendars/user/calendar.ics', methods=['GET', 'PUT', 'PROPFIND', 'REPORT'])
def handle_calendar():
    """Gère les opérations sur le calendrier"""
    if request.method == 'GET':
        # Renvoyer le calendrier
        if 'default' in calendars:
            return Response(calendars['default'], mimetype='text/calendar')
        else:
            return Response("Calendrier non trouvé", status=404)
    
    elif request.method == 'PUT':
        # Mettre à jour le calendrier
        cal_data = request.data
        save_calendar(cal_data)
        return Response("OK", status=200)
    
    elif request.method == 'PROPFIND':
        # Répondre avec les propriétés du calendrier
        xml_response = f"""<?xml version="1.0" encoding="utf-8"?>
<D:multistatus xmlns:D="DAV:" xmlns:C="urn:ietf:params:xml:ns:caldav">
  <D:response>
    <D:href>/calendars/user/calendar.ics</D:href>
    <D:propstat>
      <D:prop>
        <D:resourcetype>
          <D:collection/>
          <C:calendar/>
        </D:resourcetype>
        <D:displayname>Mon Calendrier</D:displayname>
        <C:supported-calendar-component-set>
          <C:comp name="VEVENT"/>
        </C:supported-calendar-component-set>
      </D:prop>
      <D:status>HTTP/1.1 200 OK</D:status>
    </D:propstat>
  </D:response>
</D:multistatus>"""
        
        return Response(xml_response, status=207, mimetype='application/xml')
    
    elif request.method == 'REPORT':
        # Répondre aux requêtes de rapport (utilisées pour la synchronisation)
        if 'default' in calendars:
            return Response(calendars['default'], mimetype='text/calendar')
        else:
            return Response("Calendrier non trouvé", status=404)

@app.route('/', defaults={'path': ''}, methods=['GET', 'PROPFIND'])
@app.route('/<path:path>', methods=['GET', 'PROPFIND', 'REPORT', 'PUT'])
def catch_all(path):
    """Attrape toutes les autres requêtes"""
    # Rediriger vers la racine des calendriers
    return Response('', status=301, headers={'Location': '/calendars/'})

@app.after_request
def add_header(response):
    """Ajouter les en-têtes pour la compatibilité avec Apple"""
    response.headers['DAV'] = '1, 2, 3, calendar-access, addressbook, extended-mkcol'
    response.headers['Allow'] = 'OPTIONS, GET, HEAD, POST, PUT, DELETE, TRACE, COPY, MOVE, MKCOL, PROPFIND, PROPPATCH, LOCK, UNLOCK, REPORT'
    return response

# Surveiller les modifications du fichier ICS
last_modified = 0

def check_ics_changes():
    """Vérifie si le fichier ICS a été modifié"""
    global last_modified
    try:
        mtime = os.path.getmtime(ICS_FILE_PATH)
        if mtime > last_modified:
            load_ics_file()
            last_modified = mtime
            print(f"Fichier ICS mis à jour à {datetime.fromtimestamp(mtime)}")
    except Exception as e:
        print(f"Erreur lors de la vérification du fichier ICS: {e}")

@app.before_request
def before_request():
    """Vérifie les modifications avant chaque requête"""
    check_ics_changes()

if __name__ == '__main__':
    # Initialisation
    create_default_calendar()
    load_ics_file()
    last_modified = os.path.getmtime(ICS_FILE_PATH)
    
    # Lancer le serveur
    print(f"Serveur CalDAV démarré - utilisez l'adresse IP locale de cette machine")
    print(f"Fichier ICS: {os.path.abspath(ICS_FILE_PATH)}")
    app.run(host='0.0.0.0', port=8080, debug=True)