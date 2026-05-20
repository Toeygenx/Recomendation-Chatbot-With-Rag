import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()



def get_db_connection():
    """
    Establishes a connection to the PostgreSQL database using credentials from .env.
    Returns the connection object or None if connection fails.
    """
    try:
        db_url = os.getenv('DATABASE_URL')
        if db_url:
            conn = psycopg2.connect(db_url)
        else:
            conn = psycopg2.connect(
                host=os.getenv('DB_HOST') or os.getenv('PGHOST'),
                database=os.getenv('DB_NAME') or os.getenv('PGDATABASE'),
                user=os.getenv('DB_USER') or os.getenv('PGUSER'),
                password=os.getenv('DB_PASSWORD') or os.getenv('PGPASSWORD'),
                port=os.getenv('DB_PORT') or os.getenv('PGPORT')
            )
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None
