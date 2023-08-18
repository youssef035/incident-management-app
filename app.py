import os
import sqlite3
import datetime
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename  # Import secure_filename from werkzeug.utils
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

app = Flask(__name__)
app.secret_key = '123456789'  # Replace with a secret key for secure sessions

# Initialize the LoginManager
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Sample user data (replace this with your database code)
class User(UserMixin):
    def __init__(self, user_id, username, password_hash):
        self.id = user_id
        self.username = username
        self.password_hash = password_hash

users = [
    User(2, 'ussef', generate_password_hash('ussef')),
]

# Simulate database query to get user by username
def get_user_by_username(username):
    for user in users:
        if user.username == username:
            return user
    return None

# User loader function for LoginManager
@login_manager.user_loader
def load_user(user_id):
    for user in users:
        if user.id == int(user_id):
            return user
    return None

def initialize_database():
    connection = sqlite3.connect('incident_database.db')
    cursor = connection.cursor()

    # Drop the existing table if it exists
    cursor.execute('DROP TABLE IF EXISTS incidents')

    # Create the new table with the correct schema
    cursor.execute('''
        CREATE TABLE incidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL,
            category TEXT NOT NULL,
            additional_details TEXT,
            resolution TEXT,
            escalation_level INTEGER DEFAULT 1,
            status INTEGER DEFAULT 0 CHECK (status IN (0, 1)), -- New column for incident status (0 for open, 1 for closed)
            submitted_date TEXT,  -- New column to store the date and time of submission
            closed_date TEXT  -- New column to store the date and time of closure
        )
    ''')

    connection.commit()
    connection.close()

# Function to send email notification with attachment to the IT department
def send_email_notification(recipient_email, subject, body, attachment_file=None):
    sender_email = 'fouajou035@gmail.com'  # Replace with your email address
    sender_password = 'zpjkuembyysgrgny'  # Replace with your email password

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    if attachment_file:
        with open(attachment_file, 'rb') as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename= {os.path.basename(attachment_file)}')
            msg.attach(part)

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, [recipient_email], msg.as_string())
        server.quit()
        print('Email sent successfully!')
    except Exception as e:
        print('Failed to send email.')
        print(e)

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = get_user_by_username(username)

        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash('Logged in successfully!', 'success')
            return redirect(url_for('report_incident'))
        else:
            flash('Invalid username or password', 'error')

    return render_template('login.html')

# Protected route, only accessible to logged-in users
@app.route('/', methods=['GET', 'POST'])
@login_required
def report_incident():
    if request.method == 'POST':
        incident_description = request.form['description']
        incident_category = request.form['category']
        additional_details = request.form['additional_details']
        resolution = request.form['resolution']
        escalation_level = int(request.form['escalation_level'])
        status = request.form.get('status')  # Get the status from the form (None if not provided)

        if not incident_description or not incident_category:
            return "Please provide both description and category."

        # Map the status label to the corresponding value (0 for 'pending', 1 for 'closed')
        status_mapping = {'closed': 1}
        status_value = status_mapping.get(status, 0)  # Default to 0 (pending) if status is not 'closed'

        # Get the current date and time for the submitted_date field
        submitted_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        connection = sqlite3.connect('incident_database.db')
        cursor = connection.cursor()
        cursor.execute('INSERT INTO incidents (description, category, additional_details, resolution, escalation_level, status, submitted_date) VALUES (?, ?, ?, ?, ?, ?, ?)',
                       (incident_description, incident_category, additional_details, resolution, escalation_level, status_value, submitted_date))
        connection.commit()
        connection.close()

        # Get the uploaded file and save it to a temporary directory
        attachment_file = None
        if 'attachment' in request.files:
            file = request.files['attachment']
            if file.filename:
                filename = secure_filename(file.filename)  # Use secure_filename to handle the file upload securely
                file.save(os.path.join('uploads', filename))
                attachment_file = os.path.join('uploads', filename)

        recipient_email = 'fouajou036@gmail.com'  # Replace with the IT department's email address
        subject = 'Incident Report Submitted'
        body = f"An incident report has been submitted:\n\nCategory: {incident_category}\nEscalation Level: {escalation_level}\nDescription: {incident_description}"

        if attachment_file:
            body += f"\nAttachment: {os.path.basename(attachment_file)}"

        # Call the send_email_notification function with the attachment_file parameter
        send_email_notification(recipient_email, subject, body, attachment_file)

        # Redirect the user to the view_incidents page after form submission
        return redirect(url_for('view_incidents'))

    return render_template('report_incident.html')

@app.route('/close_incident/<int:incident_id>')
@login_required
def close_incident(incident_id):
    # Get the current date and time for the closed_date field
    closed_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    connection = sqlite3.connect('incident_database.db')
    cursor = connection.cursor()
    cursor.execute('UPDATE incidents SET status = 1, closed_date = ? WHERE id = ?', (closed_date, incident_id))
    connection.commit()
    connection.close()

    return 'Incident closed successfully!'

# View Incidents route
@app.route('/view_incidents')
@login_required
def view_incidents():
    connection = sqlite3.connect('incident_database.db')
    cursor = connection.cursor()
    cursor.execute('SELECT * FROM incidents')
    incidents = cursor.fetchall()
    connection.close()
    return render_template('view_incidents.html', incidents=incidents)

if __name__ == '__main__':
    initialize_database()

    if not os.path.exists('uploads'):
        os.makedirs('uploads')
    app.run(host='127.0.0.1', port=8080, debug=True)
