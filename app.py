from flask import Flask, render_template, request, session, redirect, url_for, flash
import socket
import os
import threading
from server import tcp_load_balancer, udp_load_balancer
import sqlite3
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')
from itertools import cycle

@app.route('/')
def home():
    if 'username' in session:
        return render_template('index.html', username=session['username'])
    return render_template('index.html')

@app.route('/private_chat', methods=['GET', 'POST'])
def private_chat():
    if 'username' not in session:
        return redirect(url_for('signin'))

    current_user = session['username']
    protocol = request.form.get('protocol', 'TCP')  # Default to TCP if not specified
    receiver = request.args.get('user')  # Get the receiver's username from the query parameter

    if not receiver:
        flash("No user selected for private chat")

    if request.method == 'POST' and receiver:
        # Handle sending a private message
        message = request.form['message']
        command = f"SEND_PRIVATE_MESSAGE|{current_user}|{receiver}|{message}"

        if protocol == 'TCP':
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect(("localhost", 5001))
                sock.send(command.encode())
                response = sock.recv(1024).decode()
        elif protocol == 'UDP':
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.sendto(command.encode(), ("localhost", 5002))
                response, _ = sock.recvfrom(1024)

        if response != "OK":
            flash("Message failed to send")
        else:
            flash("Message sent successfully")

    # Fetch private chat messages if a receiver is selected
    if receiver:
        command = f"FETCH_PRIVATE_CHAT|{current_user}|{receiver}"
        if protocol == 'TCP':
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect(("localhost", 5001))
                sock.send(command.encode())
                response = sock.recv(1024).decode()
        elif protocol == 'UDP':
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.sendto(command.encode(), ("localhost", 5002))
                response, _ = sock.recvfrom(1024)

        # Parse messages from the server response
        messages = []
        for msg in response.split('|'):
            parts = msg.split('^')
            if len(parts) == 5:  # Expecting id, sender, receiver, message, timestamp
                messages.append({
                    'id': parts[0],
                    'sender': parts[1],
                    'receiver': parts[2],
                    'message': parts[3],
                    'timestamp': parts[4],
                })
    else:
        messages = []  # No messages if no receiver is selected

    # Fetch chat list (users who have chatted with the current user)
    command = f"FETCH_CHAT_LIST|{current_user}"
    if protocol == 'TCP':
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect(("localhost", 5001))
            sock.send(command.encode())
            response = sock.recv(1024).decode()
    elif protocol == 'UDP':
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.sendto(command.encode(), ("localhost", 5002))
            response, _ = sock.recvfrom(1024)
    
    chat_users = response.split('|') if response else []

    return render_template(
        'private_chat.html',
        username=current_user,
        receiver=receiver,
        messages=messages,
        chat_users=chat_users,
        protocol=protocol
    )

@app.route('/quiz', methods=['GET', 'POST'])
def quiz():
    if 'username' not in session:
        return redirect(url_for('signin'))

    if request.method == 'POST':
        selected_protocol = request.form['protocol']
        quiz_time = request.form['quiz_time']
        answers = {str(i): '|'.join(request.form.getlist(str(i))) for i in range(1, 11)}

        message = f"QUIZ|{session['username']}|" + "|".join(answers.values()) + f"|{quiz_time}"

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

@app.route('/chat', methods=['GET', 'POST'])
def chat():
    if 'username' not in session:
        return redirect(url_for('signin'))

    username = session['username']
    selected_protocol = request.form.get('protocol', 'TCP')

    if request.method == 'POST':
        if 'message' in request.form:
            # Send message
            msg_text = request.form['message']
            message = f"SEND_MESSAGE|{username}|{msg_text}"
        elif 'like' in request.form:
            # Like message
            msg_id = request.form['like']
            message = f"LIKE_MESSAGE|{msg_id}|{username}"
        elif 'dislike' in request.form:
            # Dislike message
            msg_id = request.form['dislike']
            message = f"DISLIKE_MESSAGE|{msg_id}|{username}"
        elif 'delete' in request.form:
            msg_id = request.form['delete']
            delete_type = request.form['delete_type']  # "self" or "all"
            is_admin = int(session.get('is_admin', 0))
            username = session['username']
            message = f"DELETE_MESSAGE|{msg_id}|{username}|{is_admin}|{delete_type}"
            print(message)
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
        
        flash(response)

    # Fetch messages
    message = f"FETCH_CHAT|{username}"
    if selected_protocol == 'TCP':
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect(("localhost", 5001))
            sock.send(message.encode())
            response = sock.recv(1024).decode()
            print(response)
    elif selected_protocol == 'UDP':
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.sendto(message.encode(), ("localhost", 5002))
            response, _ = sock.recvfrom(1024)
            response = response.decode()
            print(response)
    print('------fetch--------')
    print(response)
    messages = []
    for msg in response.split('|'):
        parts = msg.split('^')
        if len(parts) == 7:
            is_hidden = parts[6] == 'True'
            if not is_hidden:  # Only include messages that are not hidden
                messages.append({
                    'id': parts[0],
                    'username': parts[1],
                    'message': parts[2],
                    'likes': parts[3],
                    'dislikes': parts[4],
                    'timestamp': parts[5],
                })
        else:
            messages.append({
                    'id': parts[0],
                    'username': parts[1],
                    'message': parts[2],
                    'likes': parts[3],
                    'dislikes': parts[4],
                    'timestamp': parts[5],
                })
    print(messages)
    return render_template('chat.html', username=username, messages=messages, protocol=selected_protocol)

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

@app.route('/leaderboard', methods=['GET'])
def leaderboard():
    selected_protocol = 'TCP'
    message = f"LEADERBOARD"

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

    try:
        data = response.split('|')
        new_data = []
        for i in data:
            tmp = i.split('.')
            new_data.append(tmp)
        return render_template('leaderboard.html', data=new_data)
    except:
        return f"Failed to fetch data from server"

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
            return f"Sign-up failed: {response}"

    return render_template('signup.html')
@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('home'))

if __name__ == '__main__':
    tcp_thread = threading.Thread(target=tcp_load_balancer)
    tcp_thread.start()
    udp_thread = threading.Thread(target=udp_load_balancer)
    udp_thread.start()
    
    app.run(debug=True, use_reloader=False)
