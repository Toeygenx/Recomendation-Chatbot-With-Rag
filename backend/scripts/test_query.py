
import sys
import os
import asyncio
import json
from colorama import init, Fore, Style

# Ensure parent directory is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.engine import UniversityRAG_Engine

# Initialize colorama
init(autoreset=True)

async def test_engine():
    print(f"\n{Fore.CYAN}{'='*80}")
    print(f"{Fore.CYAN}Testing Full RAG Pipeline (Async Engine)")
    print(f"{Fore.CYAN}{'='*80}\n")
    
    try:
        engine = UniversityRAG_Engine()
    except Exception as e:
        print(f"{Fore.RED}Failed to init engine: {e}")
        return

    test_queries = [
        "วิชา 01999033 คืออะไร",  # Basic Info
        "วิชานี้เรียนยากไหม",      # Reviews (Context dependent, works better if previous context existed, but here stateless)
        "แนะนำวิชาเกี่ยวกับ AI",   # Recommend
        "สอนทำกะเพราหน่อย",      # Unclear -> Guardrail
        "หมวดอยู่ดีมีสุขมีวิชาอะไรบ้าง" # Category Search
    ]
    
    for q in test_queries:
        print(f"\n{Fore.YELLOW}Query: {q}")
        print("-" * 40)
        
        # Simulate SSE Stream Consumption
        t_start = asyncio.get_event_loop().time()
        full_response = ""
        
        try:
            generator = engine.stream_custom_query(q)
            
            async for event_str in generator:
                event = json.loads(event_str)
                evt_type = event.get("type")
                data = event # Flattened in actual usage but here it's nested
                
                if evt_type == "status":
                    print(f"{Fore.BLUE}[STATUS] {event.get('message')}")
                elif evt_type == "debug":
                    step = event.get("step")
                    # details = event.get("details") 
                    # Simplify details for print
                    print(f"{Fore.MAGENTA}[THINKING] {step}...")
                elif evt_type == "token":
                    content = event.get("content")
                    full_response += content
                    print(content, end="", flush=True)
                elif evt_type == "result":
                    print(f"\n\n{Fore.GREEN}[DONE] Latency: {event.get('latency_ms', 0):.2f}ms")
                    sources = event.get("sources", [])
                    print(f"{Fore.WHITE}Sources Used: {len(sources)}")
                    
        except Exception as e:
            print(f"\n{Fore.RED}Error: {e}")
            
        print(f"\n{'-'*40}")

if __name__ == "__main__":
    asyncio.run(test_engine())
