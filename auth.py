# auth.py

import sqlite3
import bcrypt
from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = '123456789'  # Change this to a secure secret key

# User Registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if not username or not password:
            return "Please provide both username and password."

        # Hash the password before storing it in the database
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        connection = sqlite3.connect('incident_database.db')
        cursor = connection.cursor()
        cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, hashed_password))
        connection.commit()
        connection.close()

        return 'User registered successfully!'

    return render_template('register.html')

# User Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if not username or not password:
            return "Please provide both username and password."

        connection = sqlite3.connect('incident_database.db')
        cursor = connection.cursor()
        cursor.execute('SELECT password FROM users WHERE username = ?', (username,))
        user_data = cursor.fetchone()
        connection.close()

        if user_data and bcrypt.checkpw(password.encode('utf-8'), user_data[0]):
            # User authentication successful, start a session
            session['username'] = username
            return redirect(url_for('user_dashboard'))
        else:
            return "Invalid username or password."

    return render_template('login.html')

# User Logout
@app.route('/logout')
def logout():
    # Clear the session data to log the user out
    session.clear()
    return redirect(url_for('login'))
