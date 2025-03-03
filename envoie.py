import smtplib
from email.message import EmailMessage

# Configuration SMTP
SMTP_SERVER = 'smtp-relay.brevo.com'
SMTP_PORT = 587
SMTP_USERNAME = 'namivam721@ebuthor.com'
SMTP_PASSWORD = 'NZWbLOa3mIPd6vkr'  # ⚠️ Utilise une variable d’environnement pour la sécurité !
SENDER_EMAIL = 'apple@apple-ascenseur.fr'
RECIPIENT_EMAIL = 'yassinrabhi91@gmail.com'

email_subject = "Nouvel événement ajouté à votre agenda"
email_body = "L'événement a été ajouté automatiquement à votre calendrier. Ouvrez la pièce jointe pour l'importer."

# Lecture du fichier ICS
filename = "event.ics"
with open(filename, "rb") as f:
    file_data = f.read()

# Création du message email
msg = EmailMessage()
msg["From"] = SENDER_EMAIL
msg["To"] = RECIPIENT_EMAIL
msg["Subject"] = email_subject
msg.set_content(email_body)

# Ajout du fichier ICS en pièce jointe
msg.add_attachment(file_data, maintype="text", subtype="calendar", filename=filename)

# Envoi de l'email
with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
    server.starttls()  # Sécurisation
    server.login(SMTP_USERNAME, SMTP_PASSWORD)
    server.send_message(msg)

print("Email envoyé avec succès ! 📅")
