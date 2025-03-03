from ics import Calendar, Event

# Création du calendrier
cal = Calendar()

# Création de l'événement
event = Event()
event.name = "Réunion d'orde "
event.begin = "2025-03-03 21:00:00"
event.end = "2025-03-03 23:30:00"
event.location = "Bureau 30"
event.description = "Discussion sur toi ."

# Ajout de l'événement
cal.events.add(event)

# Génération du contenu ICS en supprimant ORGANIZER et en ajoutant METHOD:PUBLISH
ics_content = "BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:-//My Calendar//EN\nMETHOD:PUBLISH\n" + cal.serialize()[15:]

# Sauvegarde du fichier .ics
filename = "event.ics"
with open(filename, "w") as f:
    f.write(ics_content)
