import sys
import os

# Add parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.ingestion import ingest_sql, ingest_chroma

if __name__ == "__main__":
    # setup_data()
    # ingest_sql()
    ingest_chroma()
