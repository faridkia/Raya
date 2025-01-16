import sqlite3
# def init_db():
#     conn = sqlite3.connect('database.db')
#     cursor = conn.cursor()
#     cursor.execute('''
#         CREATE TABLE IF NOT EXISTS users (
#             username TEXT PRIMARY KEY,
#             password TEXT NOT NULL
#         )
#     ''')
#     conn.commit()
#     conn.close()

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
print(response)