from llama_index.core.program import LLMTextCompletionProgram
from core.config import rewrite_llm
from models.schemas import QueryIntent, QueryCategory
from data.constants import FACULTY_LIST, GENED_CATEGORY_LIST

class OneShotRouter:
    def __init__(self):
        # Create comma-separated strings for the prompt
        faculty_list_str = ", ".join(FACULTY_LIST)
        category_list_str = ", ".join(GENED_CATEGORY_LIST)

        # Define the prompt template for extraction
        self.prompt_template_str = f"""
        You are an expert intent classifier for a university course chatbot (Kasetsart University).
        Classify the query into one of the following categories and extract relevant entities.

        **Intents:**
        1. **basic_info**: User asks for details of a SPECIFIC course (e.g., "What is 01999033?", "Credits for Sports").
           - REQUIRED: Extracts `course_codes` or `course_names`.
           - user ต้องถามเกี่ยวกับเรื่อง คำอธิบายรายวิชา หน่วยกิต รหัสวิชา ชื่อวิชา
           ex. วิชา 01999033 คือวิชาอะไร
           ex. วิชา 01999033 หน่วยกิตเท่าไหร่
        2. **reviews**: User asks for opinions, difficulty, teaching style, or grading of a SPECIFIC course.
           - REQUIRED: Extracts `course_codes` or `course_names`.
           - CLEANING: Remove prefixes like "วิชา" or "รายวิชา" from `course_names`. (e.g., "วิชาภาษาอังกฤษ" -> "ภาษาอังกฤษ")
           - user ต้องถามเกี่ยวกับเรื่อง ความยากง่าย รูปแบบการสอน โดยอาจจะถามในเรื่องที่อาจจะมีในรีวิวเพิ่มเติม เช่น มีสอบมั้ย เรียนออนไลน์ไหม
           - reviews คือ user ระบุชื่อวิชาหรือรหัสวิชามา
           ex. วิชา 01999033 เรียนยากไหม
           ex. ขอรีวิววิชา 01999033 หน่อย
        3. **recommend**: User asks for suggestions based on a TOPIC, KEYWORD, or CONDITION (e.g., "Easy courses", "Courses about plants", "Online courses").
           - Used when NO specific course ID is mentioned, but the user wants options.
           - user ต้องถามเกี่ยวกับเรื่อง แนะนำวิชา โดยอาจถามประมาณว่า ต้องการวิชาที่มีรีวิวแบบนี้ หรือวิชาที่มีสอนในเรื่องนี้
           - recommend คือ user ไม่ได้ระบุชื่อวิชามา เพียงแต่ถามว่าต้องการวิชาที่มีรีวิวประมาณนี้ หรือ สอนในเรื่องนี้ ช่วยแนะนำวิชานั้นหน่อย
           ex. วิชาที่คนลงเยอะๆ เทอมนี้มีอะไรบ้าง
           ex. วิชา GenEd คณะวิทย์มีตัวไหนน่าเก็บ
           ex. แนะนำวิชาที่อยู่ในหมวดอยู่ดีมีสุข
        4. **category_search**: User asks for a LIST of courses in a specific FACULTY or CATEGORY.
           - REQUIRED: Valid `Faculty` or `General Education Category` must be present.
           ex. ขอวิชาที่คณะวิทย์มีอะไรบ้าง
           ex. ขอวิชาที่หมวดอยู่ดีมีสุขมีอะไรบ้าง
           ex. คณะวิดวะมีวิชาอะไรบ้าง
        5. **chit_chat**: Greetings, thanks, or "How to use".
        6. **unclear**: Nonsense, completely off-topic (e.g., "politics", "food recipe"), or ambiguous without context.

        **VALID FACULTY LIST:**
        [{faculty_list_str}]

        **VALID GENED CATEGORIES:**
        [{category_list_str}]

        **Guidelines:**
        - **Explicit Intent Override**: If the user explicitly uses keywords like "วิชา", "รหัส", "รีวิว" followed by ANY text, classify it as `basic_info` or `reviews`.
          - **EXCEPTION (Safety Net)**: If the text contains HARMFUL, VIOLENT, SEXUALLY EXPLICIT, or ILLEGAL content (e.g., "วิชาฆ่าตัวตาย", "วิชาเย็ด", "วิชาขายยาบ้า"), MUST mark as `unclear`. Safety is priority.
          - Example: "วิชาสวัสดีซีฟู๊ด" -> `basic_info` (Pass).
          - Example: "วิชาตีกะหรี่" -> `unclear` (Block).
        - **Unclear**: If the input is random text or unrelated to the university, mark as `unclear`.
        - **Category Search**: ONLY use this if a valid Faculty or Category is explicitly mentioned or implied by the `Expanded Query`.
        - **Recommend**: Use this for broad queries like "Help me choose a course" or "Any interesting subjects?".

        **Query:** {{query_str}}

        **Output JSON:**
        """
        
        self.program = LLMTextCompletionProgram.from_defaults(
            output_cls=QueryIntent,
            llm=rewrite_llm,
            prompt_template_str=self.prompt_template_str,
            verbose=True
        )

    def route(self, query: str) -> QueryIntent:
        """
        Predicts the intent and extracts entities from the query.
        """
        try:
            response = self.program(query_str=query)
            return response
        except Exception as e:
            print(f"Error in Router: {e}")
            # Fallback
            return QueryIntent(
                category=QueryCategory.UNCLEAR, 
                reason="Router Error"
            )
