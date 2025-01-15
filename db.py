import sqlite3

def create_tables():
    connection = sqlite3.connect("users.db")
    cursor = connection.cursor()

    # Create users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )
    """)
    connection.commit()
    connection.close()

def get_db_connection():
    return sqlite3.connect("users.db")

# Initialize the database
create_tables()
