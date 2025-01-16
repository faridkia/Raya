import sqlite3
import socket
import threading
from itertools import cycle

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

import socket
import threading
from itertools import cycle

# Backend servers configuration
tcp_backends = [('127.0.0.1', 5001), ('127.0.0.1', 5003), ('127.0.0.1', 5005)]
udp_backends = [('127.0.0.1', 5002), ('127.0.0.1', 5004), ('127.0.0.1', 5006)]

# Load balancer cycling through backends
tcp_backend_cycle = cycle(tcp_backends)
udp_backend_cycle = cycle(udp_backends)

def handle_tcp_client(client_socket):
    backend = next(tcp_backend_cycle)
    backend_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    backend_socket.connect(backend)
    
    # Relay data between client and backend
    def forward(source, target):
        while True:
            data = source.recv(1024)
            if not data:
                break
            target.sendall(data)
    
    threading.Thread(target=forward, args=(client_socket, backend_socket)).start()
    threading.Thread(target=forward, args=(backend_socket, client_socket)).start()

def tcp_load_balancer():
    lb_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    lb_socket.bind(('127.0.0.1', 5001))  # Keep Flask configuration unchanged
    lb_socket.listen(5)
    print("TCP Load Balancer listening on port 5001...")
    while True:
        client_socket, addr = lb_socket.accept()
        threading.Thread(target=handle_tcp_client, args=(client_socket,)).start()

def udp_load_balancer():
    lb_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    lb_socket.bind(('127.0.0.1', 5002))  # Keep Flask configuration unchanged
    print("UDP Load Balancer listening on port 5002...")
    while True:
        data, client_addr = lb_socket.recvfrom(1024)
        backend = next(udp_backend_cycle)
        backend_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        backend_socket.sendto(data, backend)
        response, _ = backend_socket.recvfrom(1024)
        lb_socket.sendto(response, client_addr)


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
    
    elif command == "SIGNUP":
        username, password = parts[1], parts[2]
        if add_user(username, password):
            return "OK"
        else:
            return "ERROR: Username already exists"
    
    elif command == "SEND_MESSAGE":
        username, msg_text = parts[1], parts[2]
        cursor.execute("INSERT INTO messages (username, message) VALUES (?, ?)", (username, msg_text))
        conn.commit()
        conn.close()
        return "MESSAGE_SENT"

    elif command == "FETCH_CHAT":
        username = parts[1]
        cursor.execute("""
            SELECT m.id, m.username, m.message, m.likes, m.dislikes, m.timestamp,
                   CASE WHEN EXISTS (
                       SELECT 1 FROM hidden_messages WHERE hidden_messages.message_id = m.id AND hidden_messages.user = ?
                   ) THEN 'True' ELSE 'False' END AS is_hidden
            FROM messages m
            ORDER BY m.timestamp DESC
            """, (username,))
        messages = cursor.fetchall()
        conn.close()

        response = '|'.join(
            f"{msg[0]}^{msg[1]}^{msg[2]}^{msg[3]}^{msg[4]}^{msg[5]}^{msg[6]}" for msg in messages
        )
        return response

    if command == "LIKE_MESSAGE":
        msg_id, username = int(parts[1]), parts[2]
        # Check if user has already reacted
        cursor.execute("SELECT reaction FROM reactions WHERE user = ? AND message_id = ?", (username, msg_id))
        existing_reaction = cursor.fetchone()
        if existing_reaction:
            if existing_reaction[0] == 'like':
                conn.close()
                return "ALREADY_LIKED"
            else:
                # Switch from dislike to like
                cursor.execute("UPDATE reactions SET reaction = 'like' WHERE user = ? AND message_id = ?", (username, msg_id))
                cursor.execute("UPDATE messages SET likes = likes + 1, dislikes = dislikes - 1 WHERE id = ?", (msg_id,))
        else:
            # Add a new like
            cursor.execute("INSERT INTO reactions (user, message_id, reaction) VALUES (?, ?, 'like')", (username, msg_id))
            cursor.execute("UPDATE messages SET likes = likes + 1 WHERE id = ?", (msg_id,))
        conn.commit()
        conn.close()
        return "MESSAGE_LIKED"

    elif command == "DISLIKE_MESSAGE":
        msg_id, username = int(parts[1]), parts[2]
        # Check if user has already reacted
        cursor.execute("SELECT reaction FROM reactions WHERE user = ? AND message_id = ?", (username, msg_id))
        existing_reaction = cursor.fetchone()
        if existing_reaction:
            if existing_reaction[0] == 'dislike':
                conn.close()
                return "ALREADY_DISLIKED"
            else:
                # Switch from like to dislike
                cursor.execute("UPDATE reactions SET reaction = 'dislike' WHERE user = ? AND message_id = ?", (username, msg_id))
                cursor.execute("UPDATE messages SET likes = likes - 1, dislikes = dislikes + 1 WHERE id = ?", (msg_id,))
        else:
            # Add a new dislike
            cursor.execute("INSERT INTO reactions (user, message_id, reaction) VALUES (?, ?, 'dislike')", (username, msg_id))
            cursor.execute("UPDATE messages SET dislikes = dislikes + 1 WHERE id = ?", (msg_id,))
        conn.commit()
        conn.close()
        return "MESSAGE_DISLIKED"

    elif command == "DELETE_MESSAGE":
        msg_id = int(parts[1])
        username = parts[2]
        is_admin = int(parts[3])
        delete_type = parts[4]  # self or all

        # get message owner
        cursor.execute("SELECT username FROM messages WHERE id = ?", (msg_id,))
        result = cursor.fetchone()

        if not result:
            conn.close()
            return "MESSAGE_NOT_FOUND"

        message_owner = result[0]

        if delete_type == 'self':
            if username == message_owner or is_admin:
                try:
                    cursor.execute("INSERT INTO hidden_messages (user, message_id, is_hide) VALUES (?, ?, 1)", (username, msg_id))
                    conn.commit()
                    conn.close()
                    return "MESSAGE_HIDDEN_SELF"
                except sqlite3.IntegrityError:
                    conn.close()
                    return "MESSAGE_ALREADY_HIDDEN"
            else:
                conn.close()
                return "PERMISSION_DENIED"

        elif delete_type == 'all':
            if username == message_owner or is_admin:
                cursor.execute("DELETE FROM hidden_messages WHERE message_id = ?", (msg_id,))
                cursor.execute("DELETE FROM messages WHERE id = ?", (msg_id,))
                conn.commit()
                conn.close()
                return "MESSAGE_DELETED_ALL"
            else:
                conn.close()
                return "PERMISSION_DENIED"
    
    elif command == "QUIZ":
        username = parts[1]
        quiz_time = int(parts[-1])
        answers = parts[2:-1]

        question_answers = []
        for i in answers:
            question_answers.append(i[1])
        #Calculate
        score = 0
        for i in range(len(answers)):
            if answers[i][0] == question_answers[i]:
                score += 1

        #Fetch 
        cursor.execute("SELECT participation_count, highest_score FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        participation_count, highest_score = user[0] + 1, max(user[1], score)
        #Update in db
        cursor.execute("""
            UPDATE users 
            SET participation_count = ?, highest_score = ?, timer = ? 
            WHERE username = ?
        """, (participation_count, highest_score, quiz_time, username))
        conn.commit()
        conn.close()
        #Sending to app
        return f"SCORE|{score}|PARTICIPATION|{participation_count}|HIGHEST|{highest_score}|TIME|{quiz_time}"
    elif command == 'LEADERBOARD':
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("""
            SELECT username, highest_score, timer
            FROM users
            ORDER BY highest_score DESC, timer ASC
        """)
        leaderboard = cursor.fetchall()
        conn.close()
        response = ''
        #Logic
        counter2 = 0
        for i in leaderboard:
            counter = 0
            for j in i:
                if counter != 2:
                    response += str(j) +'.'
                    counter += 1
                else:
                    response += str(j)
            counter2 += 1
            if counter2 != len(leaderboard):
                response += "|"
        return f'{response}'
    conn.close()
    return "INVALID_COMMAND"

if __name__ == "__main__":
    tcp_thread = threading.Thread(target=tcp_load_balancer)
    udp_thread = threading.Thread(target=udp_load_balancer)
    tcp_thread.start()
    udp_thread.start()

