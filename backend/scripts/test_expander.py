
import sys
import os
import asyncio
from colorama import init, Fore, Style

# Ensure parent directory is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.query_expander import QueryExpander

# Initialize colorama
init(autoreset=True)

async def test_expander():
    print(f"\n{Fore.CYAN}{'='*80}")
    print(f"{Fore.CYAN}Testing Query Expander")
    print(f"{Fore.CYAN}{'='*80}\n")
    
    expander = QueryExpander()
    
    test_cases = [
        # 1. Fuzzy Faculty Matching
        {
            "query": "แนะนำวิชาวิดวะหน่อย",
            "expect_filter": {"faculty": "คณะวิศวกรรมศาสตร์"},
            "desc": "Fuzzy Faculty: 'วิดวะ' -> 'คณะวิศวกรรมศาสตร์'"
        },
        {
            "query": "วิชาของคณะประมงมีไรบ้าง",
            "expect_filter": {"faculty": "คณะประมง"},
            "desc": "Exact Faculty: 'คณะประมง'"
        },
        
        # 2. Fuzzy Category Matching
        {
            "query": "หมวดอยู่ดีมีสุขมีวิชาไรบ้าง",
            "expect_filter": {"category": "อยู่ดีมีสุข"},
            "desc": "Fuzzy Category: 'หมวดอยู่ดี' -> 'อยู่ดีมีสุข'"
        },
        {
            "query": "วิชาในกลุ่มสาระภาษากับการสื่อสาร",
            "expect_filter": {"category": "ภาษากับการสื่อสาร"},
            "desc": "Exact Category"
        },
        
        # 3. Expansion Logic
        {
            "query": "Eng 4",
            "expect_keyword": "English", 
            "desc": "Short Query Expansion"
        },
        {
            "query": "วิชา 01999033 คืออะไร",
            "expect_keyword": "01999033",
            "desc": "Specific Code Extraction"
        },
        
        # 4. Unclear / Guardrails
        {
            "query": "asdfghjkl",
            "expect_unclear": True,
            "desc": "Nonsense Detection"
        },
        {
            "query": "ข้าวมันไก่ร้านไหนอร่อย",
            "expect_unclear": True,
            "desc": "Off-topic Detection"
        },
        {
            "query": "สวัสดีครับ",
            "expect_unclear": False,
            "desc": "Greeting (Should NOT be unclear)"
        }
    ]
    
    passed = 0
    failed = 0
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n{Fore.YELLOW}[{i}] Test: {test['desc']}")
        print(f"Query: '{test['query']}'")
        
        try:
            # Expander is synchronous (wrapped in thread in engine, but sync here)
            # Check if expand is async or sync. In previous context it was sync.
            result = expander.expand(test['query'])
            
            # Check Unclear
            if test.get("expect_unclear"):
                if result.is_unclear:
                    print(f"{Fore.GREEN}✓ Correctly flagged as Unclear")
                    passed += 1
                else:
                    print(f"{Fore.RED}✗ Failed: Expected Unclear, got Valid")
                    print(f"  Reasoning: {result.reasoning}")
                    failed += 1
                continue
            
            # Check Filters
            if "expect_filter" in test:
                expected = test['expect_filter']
                actual = result.extracted_filters.dict(exclude_none=True)
                
                # Check if expected dict is subset of actual dict
                match = True
                for k, v in expected.items():
                    if actual.get(k) != v:
                        match = False
                        print(f"{Fore.RED}  Mismatch {k}: Expected '{v}', Got '{actual.get(k)}'")
                
                if match:
                    print(f"{Fore.GREEN}✓ Filters Match: {actual}")
                    passed += 1
                else:
                    print(f"{Fore.RED}✗ Filter Mismatch")
                    failed += 1
                    
            # Check Keywords
            if "expect_keyword" in test:
                keywords = [k.lower() for k in result.search_keywords]
                target = test['expect_keyword'].lower()
                if any(target in k for k in keywords) or target in result.expanded_query.lower():
                     print(f"{Fore.GREEN}✓ Found keyword/expansion: {target}")
                     passed += 1
                else:
                    print(f"{Fore.RED}✗ Keyword '{target}' not found in {keywords} or expanded query")
                    failed += 1
                    
        except Exception as e:
            print(f"{Fore.RED}✗ Error: {e}")
            failed += 1

    print(f"\n{Fore.CYAN}{'='*80}")
    print(f"Summary: Passed {passed}/{len(test_cases)}")
    print(f"{Fore.CYAN}{'='*80}\n")

if __name__ == "__main__":
    asyncio.run(test_expander())
