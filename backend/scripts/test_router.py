import sys
import os
from colorama import init, Fore, Style

# Ensure parent directory is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.router import OneShotRouter

# Initialize colorama
init(autoreset=True)

def test_router():
    """Test the consolidated category router with new 6 strict intents"""
    
    print(f"\n{Fore.CYAN}{'='*80}")
    print(f"{Fore.CYAN}Testing Router (6 Intents)")
    print(f"{Fore.CYAN}{'='*80}\n")
    
    router = OneShotRouter()
    
    # Test cases organized by NEW categories
    test_cases = [
        # 1. BASIC_INFO
        {
            "category": "basic_info",
            "queries": [
                "ขอข้อมูลวิชา 01999111 หน่อยครับ",
                "วิชาสวัสดีซีฟู๊ด เรียนเกี่ยวกับอะไร",
                "วิชา 01355101 กี่หน่วยกิต",
                "วิชา 01999033 กับ 01999041 ต่างกันยังไง", # Compare -> Basic Info
                "รายละเอียดวิชาหมู่อัญมณีและเครื่องประดับ",
            ]
        },
        # 2. REVIEWS
        {
            "category": "reviews",
            "queries": [
                "วิชาสวัสดีซีฟู๊ด เรียนยากไหมครับ",
                "01999021 ภาษาไทยเพื่อการสื่อสาร งานเยอะป่าว",
                "อ.สมชาย ใจดีไหม",
                "วิชานี้ตัดเกรดยังไง",
                "ใครเคยเรียนวิชาการเมืองโลกบ้าง รีวิวหน่อย",
            ]
        },
        # 3. RECOMMEND (Includes Recommend by Group now)
        {
            "category": "recommend",
            "queries": [
                "มีวิชาอะไรเกี่ยวกับ AI แนะนำไหม",
                "ช่วยแนะนำวิชาเสรีที่เก็บ A ง่ายๆ หน่อย",
                "แนะนำวิชาคณะวิศวะให้หน่อย", # Recommend Intent
                "ช่วยแนะนำวิชาหมวดวิทย์หน่อย", # Recommend Intent
                "อยากเรียนวิชาสนุกๆ ไม่เครียด",
                "ขอวิชาช่วยดึงเกรด",
            ]
        },
        # 4. CATEGORY_SEARCH (List / Show All)
        {
            "category": "category_search",
            "queries": [
                "หมวดอยู่ดีมีสุข มีวิชาอะไรบ้างครับ",
                "ขอรายชื่อวิชาทั้งหมดในคณะวิทยาศาสตร์",
                "วิศวะมีวิชาอะไรบ้าง", # List all
                "ขอดูรายชื่อวิชาภาษาต่างประเทศทั้งหมดหน่อย",
            ]
        },
        # 5. CHIT_CHAT
        {
            "category": "chit_chat",
            "queries": [
                "สวัสดีครับ",
                "ระบบทำอะไรได้บ้าง",
                "ขอบคุณครับ",
                "How to use chatbot",
            ]
        },
        # 6. UNCLEAR
       {
            "category": "unclear",
            "queries": [
                "ข้าวมันไก่ร้านไหนอร่อย",
                "ตึก SC45 ไปทางไหน",
                "asdfghjkl",
                "ค่าเทอมแพงไหม",
                "วิชาไหนค่าเทอมถูกสุด",
                "ลงทะเบียนวันไหน",
                "สอบวันไหน",
                "เกรดออกเมื่อไหร่", # New test case
                "ดูผลการประเมินได้ที่ไหน", # Assessment test case
            ]
        }
    ]
    
    total = 0
    passed = 0
    
    for group in test_cases:
        expected = group["category"]
        print(f"\n{Fore.YELLOW}Testing Intent: {expected.upper()}")
        
        for q in group["queries"]:
            total += 1
            try:
                # Note: In real flow, Expander runs first. 
                # Here we test Router's raw capability to classify.
                res = router.route(q)
                
                if res.category.value == expected:
                    print(f"{Fore.GREEN}✓ {q}")
                    passed += 1
                else:
                    print(f"{Fore.RED}✗ {q} -> Got: {res.category.value}")
            except Exception as e:
                print(f"{Fore.RED}Error: {e}")
                
    print(f"\n{Fore.CYAN}Summary: {passed}/{total} Passed")

if __name__ == "__main__":
    test_router()
