from flask import Flask, request, Response, redirect, make_response
import icalendar
from datetime import datetime
import os
import uuid
import pytz
import xml.etree.ElementTree as ET
import shutil
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('caldav-server')

app = Flask(__name__)

# Configuration des chemins
USER_ICS_FILE = 'calendars/user/event.ics'  # Chemin vers votre fichier .ics existant
CALENDAR_DIR = 'calendars'
ICS_FILE_PATH = f'{CALENDAR_DIR}/my_calendar.ics'
CALENDAR_URL = '/calendar/'

# Assurez-vous que le dossier des calendriers existe
os.makedirs(os.path.dirname(ICS_FILE_PATH), exist_ok=True)

# Fonction pour copier le fichier utilisateur vers le répertoire de l'application
def update_calendar_from_user_file():
    if os.path.exists(USER_ICS_FILE):
        # Assurez-vous que le dossier de destination existe
        os.makedirs(os.path.dirname(ICS_FILE_PATH), exist_ok=True)
        
        # Copier le fichier
        shutil.copy2(USER_ICS_FILE, ICS_FILE_PATH)
        logger.info(f"Fichier {USER_ICS_FILE} copié vers {ICS_FILE_PATH}")
        return True
    else:
        logger.warning(f"Attention: {USER_ICS_FILE} n'existe pas")
        return False

# Créer un exemple de fichier .ics si aucun n'existe
def create_sample_ics():
    if not os.path.exists(USER_ICS_FILE):
        # Assurez-vous que le dossier existe
        os.makedirs(os.path.dirname(USER_ICS_FILE), exist_ok=True)
        
        # Créer un calendrier avec un événement de test
        cal = icalendar.Calendar()
        cal.add('prodid', '-//My Calendar//example.com//')
        cal.add('version', '2.0')
        
        # Créer un événement de test
        event = icalendar.Event()
        event.add('summary', 'Événement Exemple')
        
        # Date de début (demain à 10h)
        start_time = datetime.now(pytz.utc).replace(hour=10, minute=0, second=0)
        event.add('dtstart', start_time)
        
        # Date de fin (demain à 11h)
        end_time = start_time.replace(hour=11)
        event.add('dtend', end_time)
        
        event.add('dtstamp', datetime.now(pytz.utc))
        event.add('uid', str(uuid.uuid4()))
        
        # Ajouter l'événement au calendrier
        cal.add_component(event)
        
        # Sauvegarder le calendrier
        with open(USER_ICS_FILE, 'wb') as f:
            f.write(cal.to_ical())
        
        logger.info(f"Fichier exemple {USER_ICS_FILE} créé")
        return True
    return False

# Afficher les routes enregistrées au démarrage
def log_routes():
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append(f"{rule} - {rule.methods}")
    logger.info(f"Routes enregistrées: {routes}")

# Appeler ces fonctions au démarrage
with app.app_context():
    log_routes()
    # Créer un exemple si nécessaire
    create_sample_ics()
    # Mettre à jour depuis le fichier utilisateur
    update_calendar_from_user_file()

# Fonction pour lire un fichier .ics
def read_ical_file(file_path):
    # D'abord, vérifier si le fichier utilisateur a été modifié
    update_calendar_from_user_file()
    
    if not os.path.exists(file_path):
        logger.warning(f"Fichier {file_path} n'existe pas, création d'un calendrier vide")
        # Créer un calendrier vide si le fichier n'existe pas
        cal = icalendar.Calendar()
        cal.add('prodid', '-//My Calendar//example.com//')
        cal.add('version', '2.0')
        
        with open(file_path, 'wb') as f:
            f.write(cal.to_ical())
    
    try:
        with open(file_path, 'rb') as f:
            cal_data = f.read()
            cal = icalendar.Calendar.from_ical(cal_data)
            
            # Compter et logger les événements
            event_count = len([c for c in cal.walk('VEVENT')])
            logger.info(f"Lecture de {file_path}: {event_count} événements trouvés")
            
            # Logger les détails des événements pour le débogage
            for i, event in enumerate(cal.walk('VEVENT')):
                summary = event.get('summary', 'Sans titre')
                uid = event.get('uid', 'Pas d\'UID')
                dtstart = event.get('dtstart', 'Pas de date de début')
                logger.info(f"Événement {i+1}: {summary}, UID: {uid}, Début: {dtstart}")
            
            return cal
    except Exception as e:
        logger.error(f"Erreur lors de la lecture du fichier {file_path}: {str(e)}")
        # En cas d'erreur, créer un calendrier vide
        cal = icalendar.Calendar()
        cal.add('prodid', '-//My Calendar//example.com//')
        cal.add('version', '2.0')
        return cal

# Fonction d'aide pour créer des réponses CalDAV
def caldav_response(status_code, headers=None, body=None):
    response = make_response(body if body else '', status_code)
    
    if headers:
        for key, value in headers.items():
            response.headers[key] = value
    
    # Headers essentiels pour CalDAV
    response.headers.setdefault('DAV', '1, calendar-access')
    response.headers.setdefault('Content-Type', 'text/xml; charset=utf-8')
    
    return response

# Redirection de l'URL de découverte de service vers le calendrier principal
@app.route('/.well-known/caldav', methods=['GET', 'PROPFIND', 'OPTIONS'])
def well_known_caldav():
    logger.info(f"Requête {request.method} sur /.well-known/caldav")
    if request.method == 'OPTIONS':
        return caldav_response(200, {
            'Allow': 'OPTIONS, GET, PROPFIND',
            'DAV': '1, 3, calendar-access'
        })
    
    # Rediriger vers le calendrier principal
    return redirect(CALENDAR_URL, code=301)

# Route pour la racine du serveur - Important pour la découverte
@app.route('/', methods=['GET', 'PROPFIND', 'OPTIONS'])
def root():
    logger.info(f"Requête {request.method} sur /")
    if request.method == 'OPTIONS':
        return caldav_response(200, {
            'Allow': 'OPTIONS, GET, PROPFIND',
            'DAV': '1, 3, calendar-access'
        })
    
    if request.method == 'PROPFIND':
        depth = request.headers.get('Depth', '0')
        logger.info(f"PROPFIND sur / avec profondeur {depth}")
        
        xml_response = f"""<?xml version="1.0" encoding="utf-8"?>
        <D:multistatus xmlns:D="DAV:" xmlns:C="urn:ietf:params:xml:ns:caldav">
            <D:response>
                <D:href>/</D:href>
                <D:propstat>
                    <D:prop>
                        <D:resourcetype>
                            <D:collection/>
                        </D:resourcetype>
                        <D:displayname>CalDAV Server</D:displayname>
                        <D:current-user-principal>
                            <D:href>/principals/users/default/</D:href>
                        </D:current-user-principal>
                    </D:prop>
                    <D:status>HTTP/1.1 200 OK</D:status>
                </D:propstat>
            </D:response>
        """
        
        if depth != '0':
            xml_response += f"""
            <D:response>
                <D:href>{CALENDAR_URL}</D:href>
                <D:propstat>
                    <D:prop>
                        <D:resourcetype>
                            <D:collection/>
                            <C:calendar/>
                        </D:resourcetype>
                        <D:displayname>Calendrier Principal</D:displayname>
                    </D:prop>
                    <D:status>HTTP/1.1 200 OK</D:status>
                </D:propstat>
            </D:response>
            """
            
        xml_response += '</D:multistatus>'
        
        return Response(xml_response, mimetype='text/xml')
    
    return "<h1>Serveur CalDAV en fonctionnement</h1>"

# Route pour gérer les chemins de découverte CalDAV supplémentaires
@app.route('/principals/', methods=['PROPFIND', 'OPTIONS'])
@app.route('/principals/users/', methods=['PROPFIND', 'OPTIONS'])
@app.route('/principals/users/default/', methods=['PROPFIND', 'OPTIONS'])
def principals():
    logger.info(f"Requête {request.method} sur {request.path}")
    if request.method == 'OPTIONS':
        return caldav_response(200, {
            'Allow': 'OPTIONS, PROPFIND',
            'DAV': '1, 3, calendar-access'
        })
    
    xml_response = """<?xml version="1.0" encoding="utf-8"?>
    <D:multistatus xmlns:D="DAV:" xmlns:C="urn:ietf:params:xml:ns:caldav">
        <D:response>
            <D:href>/principals/users/default/</D:href>
            <D:propstat>
                <D:prop>
                    <D:resourcetype>
                        <D:principal/>
                    </D:resourcetype>
                    <D:displayname>Utilisateur par défaut</D:displayname>
                    <C:calendar-home-set>
                        <D:href>/calendar/</D:href>
                    </C:calendar-home-set>
                </D:prop>
                <D:status>HTTP/1.1 200 OK</D:status>
            </D:propstat>
        </D:response>
    </D:multistatus>
    """
    return Response(xml_response, mimetype='text/xml')

# Route pour gérer les chemins de découverte alternatifs
@app.route('/calendar/dav/u/user/', methods=['PROPFIND', 'OPTIONS', 'GET'])
def calendar_alt_path():
    logger.info(f"Requête {request.method} sur {request.path}")
    # Rediriger vers le chemin de calendrier principal
    if request.method == 'GET':
        return redirect(CALENDAR_URL)
    else:
        # Pour PROPFIND/OPTIONS, rediriger vers l'URL principale du calendrier
        return redirect(CALENDAR_URL, code=301)

# Route principale pour l'accès au calendrier
@app.route('/calendar/', methods=['PROPFIND', 'REPORT', 'GET', 'OPTIONS', 'PROPPATCH'])
def calendar_root():
    logger.info(f"Requête {request.method} sur /calendar/")
    # Vérifier si le fichier utilisateur a été mis à jour
    update_calendar_from_user_file()
    
    if request.method == 'OPTIONS':
        return caldav_response(200, {
            'Allow': 'OPTIONS, GET, PROPFIND, REPORT, PROPPATCH',
            'DAV': '1, 3, calendar-access'
        })
    
    if request.method == 'PROPPATCH':
        # Pour l'instant, nous simulons une réponse positive sans modifier quoi que ce soit
        logger.info("PROPPATCH reçu - simulant une réponse positive")
        xml_response = """<?xml version="1.0" encoding="utf-8"?>
        <D:multistatus xmlns:D="DAV:">
            <D:response>
                <D:href>/calendar/</D:href>
                <D:propstat>
                    <D:prop>
                    </D:prop>
                    <D:status>HTTP/1.1 200 OK</D:status>
                </D:propstat>
            </D:response>
        </D:multistatus>
        """
        return Response(xml_response, mimetype='text/xml')
    
    if request.method == 'PROPFIND':
        # Obtenir les en-têtes pour personnaliser la réponse
        depth = request.headers.get('Depth', '0')
        logger.info(f"PROPFIND sur /calendar/ avec profondeur {depth}")
        
        try:
            # Analyser la requête XML si elle existe
            request_xml = None
            if request.data:
                request_xml = ET.fromstring(request.data)
                logger.debug(f"Requête XML reçue: {request.data.decode('utf-8')[:200]}...")
        except Exception as e:
            # Si l'analyse échoue, continuer sans elle
            logger.error(f"Erreur lors de l'analyse XML: {str(e)}")
            request_xml = None
        
        # Réponse basique pour PROPFIND
        xml_response = f"""<?xml version="1.0" encoding="utf-8"?>
        <D:multistatus xmlns:D="DAV:" xmlns:C="urn:ietf:params:xml:ns:caldav" xmlns:CS="http://calendarserver.org/ns/">
            <D:response>
                <D:href>{CALENDAR_URL}</D:href>
                <D:propstat>
                    <D:prop>
                        <D:resourcetype>
                            <D:collection/>
                            <C:calendar/>
                        </D:resourcetype>
                        <D:displayname>Calendrier Principal</D:displayname>
                        <C:supported-calendar-component-set>
                            <C:comp name="VEVENT"/>
                        </C:supported-calendar-component-set>
                        <D:owner>
                            <D:href>/principals/users/default/</D:href>
                        </D:owner>
                        <D:current-user-principal>
                            <D:href>/principals/users/default/</D:href>
                        </D:current-user-principal>
                        <C:calendar-timezone>BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Example Corp.//CalDAV Server//EN
BEGIN:VTIMEZONE
TZID:Europe/Paris
BEGIN:STANDARD
DTSTART:20201025T030000
RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU
TZOFFSETFROM:+0200
TZOFFSETTO:+0100
END:STANDARD
BEGIN:DAYLIGHT
DTSTART:20200329T020000
RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU
TZOFFSETFROM:+0100
TZOFFSETTO:+0200
END:DAYLIGHT
END:VTIMEZONE
END:VCALENDAR
                        </C:calendar-timezone>
                    </D:prop>
                    <D:status>HTTP/1.1 200 OK</D:status>
                </D:propstat>
            </D:response>
        """
        
        # Si la profondeur est 1, inclure les événements
        if depth != '0':
            cal = read_ical_file(ICS_FILE_PATH)
            
            # Ajouter chaque événement à la réponse
            for component in cal.walk('VEVENT'):
                event_uid = component.get('uid', uuid.uuid4())
                event_data = component.to_ical().decode('utf-8')
                
                xml_response += f"""
                <D:response>
                    <D:href>/calendar/{event_uid}.ics</D:href>
                    <D:propstat>
                        <D:prop>
                            <D:getetag>"{hash(event_data)}"</D:getetag>
                            <D:resourcetype/>
                        </D:prop>
                        <D:status>HTTP/1.1 200 OK</D:status>
                    </D:propstat>
                </D:response>
                """
        
        xml_response += '</D:multistatus>'
        return Response(xml_response, mimetype='text/xml')
    
    elif request.method == 'REPORT':
        # Pour un REPORT, nous retournons les événements du calendrier
        logger.info(f"REPORT sur /calendar/")
        cal = read_ical_file(ICS_FILE_PATH)
        
        # Construire la réponse XML pour les événements
        xml_response = '<?xml version="1.0" encoding="utf-8"?>\n'
        xml_response += '<D:multistatus xmlns:D="DAV:" xmlns:C="urn:ietf:params:xml:ns:caldav">\n'
        
        # Compter les événements pour le débogage
        event_count = 0
        
        # Ajouter chaque événement dans la réponse
        for component in cal.walk('VEVENT'):
            event_count += 1
            event_uid = component.get('uid', uuid.uuid4())
            event_data = component.to_ical().decode('utf-8')
            summary = component.get('summary', 'Sans titre')
            
            logger.info(f"Ajout de l'événement '{summary}' (UID: {event_uid}) à la réponse REPORT")
            
            xml_response += f"""  <D:response>
    <D:href>/calendar/{event_uid}.ics</D:href>
    <D:propstat>
        <D:prop>
            <D:getetag>"{hash(event_data)}"</D:getetag>
            <C:calendar-data>{event_data}</C:calendar-data>
        </D:prop>
        <D:status>HTTP/1.1 200 OK</D:status>
    </D:propstat>
  </D:response>\n"""
        
        xml_response += '</D:multistatus>'
        logger.info(f"REPORT terminé, {event_count} événements inclus dans la réponse")
        return Response(xml_response, mimetype='text/xml')
    
    elif request.method == 'GET':
        # Afficher une page simple pour vérifier que tout fonctionne
        update_result = "Fichier utilisateur trouvé et utilisé" if os.path.exists(USER_ICS_FILE) else "Attention: Fichier utilisateur non trouvé"
        
        # Obtenir des informations sur les événements
        events_info = ""
        try:
            cal = read_ical_file(ICS_FILE_PATH)
            events = list(cal.walk('VEVENT'))
            
            if events:
                events_info = f"<h2>Événements trouvés ({len(events)})</h2><ul>"
                for event in events:
                    summary = event.get('summary', 'Sans titre')
                    uid = event.get('uid', 'Pas d\'UID')
                    dtstart = event.get('dtstart', 'Pas de date de début')
                    events_info += f"<li><strong>{summary}</strong> - UID: {uid}, Début: {dtstart}</li>"
                events_info += "</ul>"
            else:
                events_info = "<h2>Aucun événement trouvé dans le fichier .ics</h2>"
        except Exception as e:
            events_info = f"<h2>Erreur lors de la lecture des événements: {str(e)}</h2>"
        
        return f"""
        <h1>Serveur CalDAV en fonctionnement</h1>
        <p>{update_result}</p>
        <p>Fichier utilisé: {USER_ICS_FILE}</p>
        <p>Fichier du serveur: {ICS_FILE_PATH}</p>
        {events_info}
        <p><a href="/update_from_user_file">Forcer la mise à jour depuis le fichier utilisateur</a></p>
        <p><a href="/create_sample_event">Créer un événement exemple</a></p>
        """

# Route pour accéder à un événement spécifique
@app.route('/calendar/<event_id>.ics', methods=['GET'])
def get_event(event_id):
    logger.info(f"Requête GET pour l'événement {event_id}")
    cal = read_ical_file(ICS_FILE_PATH)
    
    # Rechercher l'événement par son ID
    for component in cal.walk('VEVENT'):
        if str(component.get('uid', '')) == event_id:
            # Créer un nouveau calendrier avec juste cet événement
            event_cal = icalendar.Calendar()
            event_cal.add('prodid', '-//My Calendar//example.com//')
            event_cal.add('version', '2.0')
            event_cal.add_component(component)
            
            logger.info(f"Événement {event_id} trouvé et renvoyé")
            return Response(event_cal.to_ical(), mimetype='text/calendar')
    
    logger.warning(f"Événement {event_id} non trouvé")
    return "Événement non trouvé", 404

# Route pour forcer la mise à jour depuis le fichier utilisateur
@app.route('/update_from_user_file', methods=['GET'])
def force_update():
    logger.info("Mise à jour forcée demandée")
    result = update_calendar_from_user_file()
    if result:
        return """
        <h1>Calendrier mis à jour avec succès</h1>
        <p>Le calendrier a été mis à jour à partir de calendars/user/event.ics</p>
        <p><a href="/">Retour à la page d'accueil</a></p>
        """
    else:
        return """
        <h1>Erreur de mise à jour</h1>
        <p>Impossible de mettre à jour le calendrier. Vérifiez que le fichier calendars/user/event.ics existe.</p>
        <p><a href="/create_sample_event">Créer un événement exemple</a></p>
        <p><a href="/">Retour à la page d'accueil</a></p>
        """, 404

# Route pour créer un événement exemple
@app.route('/create_sample_event', methods=['GET'])
def create_sample_event():
    logger.info("Création d'un événement exemple demandée")
    # Créer un calendrier avec un événement de test
    cal = icalendar.Calendar()
    cal.add('prodid', '-//My Calendar//example.com//')
    cal.add('version', '2.0')
    
    # Créer un événement de test
    event = icalendar.Event()
    event.add('summary', 'Événement Exemple ' + datetime.now().strftime('%H:%M:%S'))
    
    # Date de début (demain à 10h)
    start_time = datetime.now(pytz.utc).replace(hour=10, minute=0, second=0)
    event.add('dtstart', start_time)
    
    # Date de fin (demain à 11h)
    end_time = start_time.replace(hour=11)
    event.add('dtend', end_time)
    
    event.add('dtstamp', datetime.now(pytz.utc))
    event.add('uid', str(uuid.uuid4()))
    
    # Ajouter l'événement au calendrier
    cal.add_component(event)
    
    # Sauvegarder le calendrier dans le fichier utilisateur
    os.makedirs(os.path.dirname(USER_ICS_FILE), exist_ok=True)
    with open(USER_ICS_FILE, 'wb') as f:
        f.write(cal.to_ical())
    
    # Mettre à jour le calendrier du serveur
    update_calendar_from_user_file()
    
    return """
    <h1>Événement exemple créé</h1>
    <p>Un nouvel événement a été créé et ajouté au calendrier.</p>
    <p><a href="/">Retour à la page d'accueil</a></p>
    """

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)