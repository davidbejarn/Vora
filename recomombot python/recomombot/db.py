import mysql.connector
from mysql.connector import errorcode

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "admin",  
    "database": "recomombot"
}

def get_connection():
    return mysql.connector.connect(**DB_CONFIG)

def create_tables():
    """Crear DB y tablas si no existen."""
    try:
       
        conn = mysql.connector.connect(
            host=DB_CONFIG["host"],
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"]
        )
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['database']}")
        cursor.close()
        conn.close()

        # crear tablas
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INT AUTO_INCREMENT PRIMARY KEY,
                nombre VARCHAR(100),
                email VARCHAR(150) UNIQUE,
                password_hash VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS Historial (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT,
                mensaje TEXT,
                respuesta TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES usuarios(id) ON DELETE CASCADE
            )
        """)
        conn.commit()
        cur.close()
        conn.close()
        print("Tablas verificadas/creadas correctamente.")
    except mysql.connector.Error as err:
        print("Error al crear tablas:", err)

