from llama_index.core.program import LLMTextCompletionProgram
from core.config import rewrite_llm
from models.schemas import ExpandedQuery
from data.constants import FACULTY_LIST, GENED_CATEGORY_LIST

class QueryExpander:
    def __init__(self):
        # Create comma-separated strings for the prompt
        faculty_list_str = ", ".join(FACULTY_LIST)
        category_list_str = ", ".join(GENED_CATEGORY_LIST)

        self.prompt_template_str = f"""
        You are an expert query analyst for a university chatbot (Kasetsart University).
        Your goal is to clarify the user's intent, extract search keywords, and identify specific filters.

        **VALID FACULTY LIST (Exact Names Only):**
        [{faculty_list_str}]

        **VALID GENED CATEGORIES (Exact Names Only):**
        [{category_list_str}]

        **Instructions:**
        1. **Analyze** the user's query carefully.
        2. **Expand** the query:
           - If short/ambiguous (e.g., "Eng 4"), interpret it in the context of university courses (e.g., "Show courses in English languages category").
           - If it's a specific question, keep it clear (e.g., "01999033 teaches what?" -> "What are the details of course 01999033?").
        3. **Extract Filters (Map to CLOSEST match)**:
           - **For Faculties**: Map the user's input to the CLOSEST match in the **VALID FACULTY LIST**.
             - Example: "วิดวะ" -> "คณะวิศวกรรมศาสตร์"
             - Example: "ประมง" -> "คณะประมง"
             - Example: "ศิลปศาสตร์" -> "คณะศิลปศาสตร์และวิทยาศาสตร์" (or closest match)
           - **For Categories**: Map the user's input to the CLOSEST match in the **VALID GENED CATEGORIES**.
             - Example: "หมวดอยู่ดี" -> "อยู่ดีมีสุข"
             - Example: "หมวดพลเมือง" -> "พลเมืองไทยและพลเมืองโลก"
             - Example: "หมวดภาษา" -> "ภาษากับการสื่อสาร"
           - If not mentioned or no close match, set to null.
        4. **Search Keywords**:
           - detailed, specific terms for vector search.
           - If user asks for "easy grade", include keywords like "easy", "good grade", "A".
        5. **Unclear/Nonsense**:
           - If the input is random characters (e.g., "asdf", "gjs"), offensive, or completely unrelated to general conversation or courses (e.g. "recipe for bomb"), set `is_unclear` to True.
           - Greetings (Hi, Hello, Thank you) are NOT unclear.

        **Examples:**
        - "ขอข้อมูลเกี่ยวกับ Arts of living" -> expanded="Show details of course 'Arts of living'", keywords=["Arts of living"], is_unclear=False
        - "วิชา 01999033 คืออะไร" -> expanded="What is course 01999033?", keywords=["01999033"], is_unclear=False
        - "มีวิชาเกี่ยวกับ AI ไหม" -> expanded="List courses related to AI", keywords=["AI", "Artificial Intelligence"], is_unclear=False
        
        # Recommend vs Category Search Examples: (Recommend = "Suggest/Help me choose", Category Search = "List all/Show list")
        - "แนะนำวิชาคณะวิศวะให้หน่อย" -> expanded="Recommend courses in Faculty of Engineering", filters={{faculty: "คณะวิศวกรรมศาสตร์"}}, is_unclear=False
        - "ช่วยแนะนำวิชาหมวดวิทย์หน่อย" -> expanded="Recommend courses in Science category", filters={{category: "วิทยาศาสตร์และคณิตศาสตร์"}}, is_unclear=False
        - "อยากเรียนวิชาภาษาที่สนุกๆ" -> expanded="Recommend fun courses in Language category", keywords=["fun", "enjoyable"], filters={{category: "ภาษากับการสื่อสาร"}}, is_unclear=False
        
        - "หมวดอยู่ดีมีสุขมีวิชาอะไรบ้าง" -> expanded="List courses in Well-being category", filters={{category: "อยู่ดีมีสุข"}}, is_unclear=False
        - "วิศวะมีวิชาอะไรบ้าง" -> expanded="List all courses in Faculty of Engineering", filters={{faculty: "คณะวิศวกรรมศาสตร์"}}, is_unclear=False
        - "ขอดูรายชื่อวิชาในคณะประมง" -> expanded="Show full list of courses in Faculty of Fisheries", filters={{faculty: "คณะประมง"}}, is_unclear=False

        - "แนะนำวิชาเสรีสนุกๆ" -> expanded="Recommend fun free elective courses", keywords=["สนุก", "fun", "intersting"], is_unclear=False
        - "สวัสดีครับ" -> expanded="Hello", is_unclear=False
        - "how to use chatbot" -> expanded="How to use the chatbot", is_unclear=False
        - "ขอบคุณครับ" -> expanded="Thank you", is_unclear=False
        - "ข้าวมันไก่ร้านไหนอร่อย" -> is_unclear=True
        - "asdfgh" -> is_unclear=True
        - "วิชา 01999033 ยากไหม" -> expanded="Is course 01999033 difficult?", keywords=["01999033", "difficulty", "hard"], is_unclear=False
        - "ขอวิชาที่เรียนออนไลน์" -> expanded="Recommend online courses", keywords=["online learning", "online"], is_unclear=False
        - "มีวิชาอะไรที่ไม่เช็คชื่อบ้าง" -> expanded="Recommend courses that do not check attendance", keywords=["no attendance check", "attendance"], is_unclear=False

        Query: {{query_str}}

        Output JSON:
        """

        self.program = LLMTextCompletionProgram.from_defaults(
            output_cls=ExpandedQuery,
            llm=rewrite_llm,
            prompt_template_str=self.prompt_template_str,
            verbose=True
        )

    def expand(self, query: str) -> ExpandedQuery:
        """
        Expands the user query to be more specific and extracts filters.
        """
        try:
            response = self.program(query_str=query)
            return response
        except Exception as e:
            print(f"Error in QueryExpander: {e}")
            # Fallback
            return ExpandedQuery(
                expanded_query=query, 
                search_keywords=[query], 
                reasoning="Error in expansion, using original query."
            )
