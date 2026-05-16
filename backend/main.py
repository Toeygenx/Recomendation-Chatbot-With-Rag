import sys
import os

# Ensure current dir is in path to resolve packages
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.engine import UniversityRAG_Engine

def ask_bot(engine: UniversityRAG_Engine, query: str):
    response = engine.custom_query(query)
    return response

if __name__ == "__main__":
    print("Initializing RAG Engine...")
    try:
        engine = UniversityRAG_Engine()
        print("RAG System Ready. Type 'exit' to quit.")
        
        while True:
            user_input = input("User: ")
            if user_input.lower() in ["exit", "quit", "q"]:
                break
                
            response = ask_bot(engine, user_input)
            print("-" * 50)
            print(f"Bot: {response}")
            print("-" * 50)
            
    except Exception as e:
        print(f"Initialization Failed: {e}")
