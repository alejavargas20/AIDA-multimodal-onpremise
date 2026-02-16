# aida-multimodal-onpremise/backend/db/connection.py
import pyodbc

def get_db():
    return pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=localhost\SQLEXPRESS;"
        "DATABASE=AIDA_DATA;"
        "Trusted_Connection=yes;"
    )
