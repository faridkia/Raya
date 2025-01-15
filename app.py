from flask import Flask, render_template, request, session, redirect, url_for
import socket
import os
import threading
from server import handle_tcp, handle_udp
import sqlite3
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

@app.route('/')
def home():
    if 'username' in session:
        return f"Welcome, {session['username']}! <a href='/logout'>Logout</a> <a href='/quiz'>Take Quiz</a>"
    return render_template('index.html')

@app.route('/quiz', methods=['GET', 'POST'])
def quiz():
    if 'username' not in session:
        return redirect(url_for('signin'))

    if request.method == 'POST':
        selected_protocol = request.form['protocol']
        quiz_time = request.form['quiz_time']
        answers = {str(i): '|'.join(request.form.getlist(str(i))) for i in range(1, 11)}

        message = f"QUIZ|{session['username']}|" + "|".join(answers.values()) + f"|{quiz_time}"
        print('--------------Client-----------')
        print(message)
        print('--------------Client-----------')

        # Send message to server
        if selected_protocol == 'TCP':
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect(("localhost", 5001))
                sock.send(message.encode())
                response = sock.recv(1024).decode()

        elif selected_protocol == 'UDP':
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.sendto(message.encode(), ("localhost", 5002))
                response, _ = sock.recvfrom(1024)
                response = response.decode()

        # Process the response
        data = response.split('|')
        score = data[1]
        participation_count = data[3]
        highest_score = data[5]

        # Fetch sorted leaderboard
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("""
            SELECT username, highest_score, timer
            FROM users
            ORDER BY highest_score DESC, timer ASC
        """)
        leaderboard = cursor.fetchall()
        conn.close()

        # Render the results page
        return render_template(
            'quiz_results.html',
            score=score,
            participation_count=participation_count,
            highest_score=highest_score,
            leaderboard=leaderboard,
        )

    # Generate random quiz questions
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM questions ORDER BY RANDOM() LIMIT 10")
    questions = cursor.fetchall()
    conn.close()
    return render_template('quiz.html', questions=questions)


@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        selected_protocol = request.form['protocol']
        
        message = f"SIGNIN|{username}|{password}"

        if selected_protocol == 'TCP':
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect(("localhost", 5001))
                sock.send(message.encode())
                response = sock.recv(1024).decode()

        elif selected_protocol == 'UDP':
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.sendto(message.encode(), ("localhost", 5002))
                response, _ = sock.recvfrom(1024)
                response = response.decode()

        if response == "OK":
            session['username'] = username
            return redirect(url_for('home'))
        else:
            return f"Sign-in failed: {response}"

    return render_template('signin.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        selected_protocol = request.form['protocol']

        message = f"SIGNUP|{username}|{password}"

        if selected_protocol == 'TCP':
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect(("localhost", 5001))
                sock.send(message.encode())
                response = sock.recv(1024).decode()

        elif selected_protocol == 'UDP':
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.sendto(message.encode(), ("localhost", 5002))
                response, _ = sock.recvfrom(1024)
                response = response.decode()

        if response == "OK":
            session['username'] = username
            return redirect(url_for('home'))
        else:
            return f"Sign-in failed: {response}"

    return render_template('signin.html')
@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('home'))

if __name__ == '__main__':
    tcp_thread = threading.Thread(target=handle_tcp)
    tcp_thread.start()
    udp_thread = threading.Thread(target=handle_udp)
    udp_thread.start()
    
    app.run(debug=True, use_reloader=False)
