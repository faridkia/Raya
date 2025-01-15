import sqlite3
import socket
import threading

# Database initialization
def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def add_user(username, password):
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False

def authenticate_user(username, password):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT password FROM users WHERE username = ?', (username,))
    row = cursor.fetchone()
    conn.close()
    if row and row[0] == password:
        return True
    return False

import socket
import threading
import sqlite3

def handle_tcp():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('127.0.0.1', 5001))
    server.listen(5)
    print("TCP server listening...")
    while True:
        conn, addr = server.accept()
        message = conn.recv(1024).decode()
        response = message_process(message)
        conn.sendall(response.encode())

def handle_udp():
    server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server.bind(('127.0.0.1', 5002))
    print("UDP server listening...")
    while True:
        message, addr = server.recvfrom(1024)
        response = message_process(message.decode())
        server.sendto(response.encode(), addr)

def message_process(message):
    parts = message.split('|')
    command = parts[0]

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    if command == "SIGNIN":
        username, password = parts[1], parts[2]
        cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
        user = cursor.fetchone()
        conn.close()
        if user:
            return "OK"
        else:
            return "INVALID_CREDENTIALS"

    elif command == "QUIZ":
        username = parts[1]
        answers = parts[2:]


        question_answers = []
        for i in answers:
            question_answers.append(i[1])

        score = 0
        for i in range(len(answers)):
            if answers[i][0] == question_answers[i]:
                print("----Server----")
                print(answers[i][0], question_answers[i])

                score += 1
        
        # Update user's participation_count and highest_score
        cursor.execute("SELECT participation_count, highest_score FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        participation_count, highest_score = user[0] + 1, max(user[1], score)

        cursor.execute("UPDATE users SET participation_count = ?, highest_score = ? WHERE username = ?", 
                       (participation_count, highest_score, username))
        conn.commit()
        conn.close()

        return f"SCORE|{score}|PARTICIPATION|{participation_count}|HIGHEST|{highest_score}"

    return "INVALID_COMMAND"

if __name__ == "__main__":
    tcp_thread = threading.Thread(target=handle_tcp)
    udp_thread = threading.Thread(target=handle_udp)
    tcp_thread.start()
    udp_thread.start()
