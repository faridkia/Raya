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
        answer1 = '|'.join(request.form.getlist('1'))
        answer2 = '|'.join(request.form.getlist('2'))
        answer3 = '|'.join(request.form.getlist('3'))
        answer4 = '|'.join(request.form.getlist('4'))
        answer5 = '|'.join(request.form.getlist('5'))
        answer6 = '|'.join(request.form.getlist('6'))
        answer7 = '|'.join(request.form.getlist('7'))
        answer8 = '|'.join(request.form.getlist('8'))
        answer9 = '|'.join(request.form.getlist('9'))
        answer10 = '|'.join(request.form.getlist('10'))

        message = f"QUIZ|{session['username']}|{answer1}|{answer2}|{answer3}|{answer4}|{answer5}|{answer6}|{answer7}|{answer8}|{answer9}|{answer10}"
        print('--------------Client-----------')
        print(message)
        print('--------------Client-----------')

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

        data = response.split('|')
        print(data)
        score, participation_count, highest_score = data[1], data[3], data[5]

        return f"Quiz Complete! Your score: {score}/10. Participation Count: {participation_count}. Highest Score: {highest_score}. <a href='/'>Go Home</a>"

    # Generate random quiz (this will request questions from the server)
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
