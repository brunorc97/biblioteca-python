import mysql.connector

def conectar():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password=None,   # <- sem senha
        database="biblioteca_db"
    )