from typing import List, Optional, Set
from llama_index.core import VectorStoreIndex
from llama_index.core.schema import NodeWithScore, TextNode
from llama_index.core.vector_stores import MetadataFilters, MetadataFilter, FilterOperator
from models.schemas import QueryIntent, QueryCategory, ExpandedQuery
from core.database import get_db_connection
from core.config import TOP_K_RETRIEVAL, TOP_K_RERANK, rerank_llm

class StrategyRetriever:
    def __init__(self, index: VectorStoreIndex):
        self._index = index

    def _get_sql_summaries(self, target_course_ids: List[str]) -> List[NodeWithScore]:
        """Fetch course summaries directly from SQL."""
        if not target_course_ids:
            return []
            
        nodes = []
        conn = get_db_connection()
        if not conn:
            return []
            
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT course_id, summary_content, score_difficulty, score_workload, score_grading 
                FROM summary_reviews 
                WHERE course_id = ANY(%s)
            """, (target_course_ids,))
            rows = cur.fetchall()
            
            for r in rows:
                c_id, content, diff, work, grad = r
                if content:
                    node = TextNode(
                        text=f"บทสรุปรีวิววิชา {c_id}:\n{content}",
                        metadata={
                            "course_id": c_id,
                            "type": "summary_review",
                            "difficulty": diff, 
                            "workload": work, 
                            "grading": grad
                        }
                    )
                    # High base score for summaries
                    nodes.append(NodeWithScore(node=node, score=2.0))
        except Exception as e:
            print(f"Error fetching SQL summaries: {e}")
        finally:
            if conn: conn.close()
        return nodes

    def _rerank_nodes(self, query: str, nodes: List[NodeWithScore], top_n: int = TOP_K_RERANK) -> List[NodeWithScore]:
        """
        Rerank nodes using LLM with Strict Filtering (Score > 7).
        """
        if not nodes:
            return []
            
        # Format candidates
        candidates_str = ""
        for i, node in enumerate(nodes):
            candidates_str += f"[{i}] {node.node.get_text()[:500]}...\n\n"

        prompt = f"""
        You are an expert relevance filter for a university chatbot.
        User Query: "{query}"

        Rate the relevance of each document to the query on a scale of 0-10.
        
        **Scoring Criteria**:
        - **10 (Perfect)**: Exact answer or core information requested.
        - **7-9 (High)**: Very relevant, contains key details needed.
        - **4-6 (Medium)**: Related topic but misses the specific answer.
        - **0-3 (Low)**: Irrelevant, off-topic, or wrong context.

        Documents:
        {candidates_str}

        **Instructions**:
        - Analyze each document against the query.
        - assign a score (0-10).
        - **Important**: For "recommendation" queries (e.g., "easy grade", "interesting"), allow **IMPLICIT MATCHES**.
          - Ex: If user asks for "good grade" and document says "no exam" or "easy to pass", give High Score (7-9).
        - **Output Format**: "Index: Score", one per line.
        - Return ONLY documents with Score >= 5.
        - Sort by Score descending.
        
        Example Output:
        0: 10
        3: 8
        1: 7
        """

        try:
            response = rerank_llm.complete(prompt).text.strip()
            
            # Parse response "0: 10\n 3: 8"
            selected_indices = []
            lines = response.split('\n')
            
            scored_candidates = []
            
            for line in lines:
                if ":" in line:
                    parts = line.split(":")
                    if len(parts) >= 2:
                        idx_str = parts[0].strip()
                        score_str = parts[1].strip()
                        if idx_str.isdigit():
                            idx = int(idx_str)
                            # Handle score sometimes having extra text
                            import re
                            score_match = re.search(r'\d+', score_str)
                            if score_match:
                                score = int(score_match.group())
                                if score >= 5 and 0 <= idx < len(nodes):
                                    scored_candidates.append((idx, score))

            # Deduplicate by index just in case
            seen = set()
            unique_candidates = []
            for idx, score in scored_candidates:
                if idx not in seen:
                    unique_candidates.append((idx, score))
                    seen.add(idx)

            # Sort by score desc
            unique_candidates.sort(key=lambda x: x[1], reverse=True)
            
            # Slice top_n
            final_selection = unique_candidates[:top_n]
            
            reranked_nodes = []
            for idx, score in final_selection:
                node = nodes[idx]
                node.score = float(score) # Update score to the LLM's relevance score
                reranked_nodes.append(node)
                    
            print(f"Reranking (Strict): Selected {len(reranked_nodes)}/{len(nodes)} nodes (Threshold >= 5).")
            return reranked_nodes

        except Exception as e:
            print(f"LLM Reranking Error: {e}. Returning original top {top_n}")
            return nodes[:top_n]

    def _deduplicate_nodes(self, nodes: List[NodeWithScore]) -> List[NodeWithScore]:
        """Merge duplicate nodes (by ID), keeping the highest score."""
        unique_map = {}
        for node in nodes:
            nid = node.node.node_id
            if nid not in unique_map:
                unique_map[nid] = node
            else:
                if node.score > unique_map[nid].score:
                    unique_map[nid] = node
        return list(unique_map.values())

    def retrieve(
        self, 
        intent: QueryIntent, 
        expanded_data: ExpandedQuery,
        course_ids: List[str]
    ) -> List[NodeWithScore]:
        
        category = intent.category
        query_str = expanded_data.expanded_query
        keywords = expanded_data.search_keywords
        filters_data = expanded_data.extracted_filters

        nodes = []
        retriever = self._index.as_retriever(similarity_top_k=TOP_K_RETRIEVAL)

        # ---------------------------------------------------------
        # 1. BASIC INFO
        # ---------------------------------------------------------
        if category == QueryCategory.BASIC_INFO:
            if course_ids:
                # SQL Summary
                summary_nodes = self._get_sql_summaries(course_ids)
                
                # Vector Search (Description Only)
                filters = MetadataFilters(filters=[
                    MetadataFilter(key="course_id", value=course_ids, operator=FilterOperator.IN),
                    MetadataFilter(key="type", value="desc"),
                ])
                try:
                    desc_nodes = self._index.as_retriever(filters=filters, similarity_top_k=5).retrieve(query_str)
                    nodes = summary_nodes + desc_nodes
                except:
                    nodes = summary_nodes

        # ---------------------------------------------------------
        # 2. REVIEWS
        # ---------------------------------------------------------
        elif category == QueryCategory.REVIEWS:
            if course_ids:
                # SQL Summary (Always Primary)
                summary_nodes = self._get_sql_summaries(course_ids)
                
                # Vector Search (Reviews)
                filters = MetadataFilters(filters=[
                    MetadataFilter(key="course_id", value=course_ids, operator=FilterOperator.IN),
                    MetadataFilter(key="type", value="review"),
                ])
                # Fetch more candidates for Reranking
                raw_reviews = self._index.as_retriever(filters=filters, similarity_top_k=6).retrieve(query_str)
                
                # LLM Reranking
                reranked_reviews = self._rerank_nodes(query_str, raw_reviews, top_n=TOP_K_RERANK)
                
                nodes = summary_nodes + reranked_reviews

        # ---------------------------------------------------------
        # 3. RECOMMEND (Multi-query + Rerank)
        # ---------------------------------------------------------
        elif category == QueryCategory.RECOMMEND:
            # 1. Prepare Multi-queries
            queries_to_run = [query_str] + keywords
            queries_to_run = list(set(queries_to_run))[:5] # Limit to 5 variations
            print(f"Processing Recommend: Running {len(queries_to_run)} variations: {queries_to_run}")

            # 2. Prepare Base Metadata Filters (Faculty/Category)
            base_filters = []
            if filters_data.faculty:
                print(f"Filter Applied: Faculty = {filters_data.faculty}")
                base_filters.append(MetadataFilter(key="faculty", value=filters_data.faculty))
            if filters_data.category:
                print(f"Filter Applied: Category = {filters_data.category}")
                base_filters.append(MetadataFilter(key="category_64", value=filters_data.category))

            # 3. Split Search: (Desc Only) + (Summary Only)
            # This ensures we get both official info and AI summaries, but exclude raw reviews
            all_nodes: List[NodeWithScore] = []
            
            # 3.1 Search for Type=desc
            filters_desc = base_filters.copy()
            filters_desc.append(MetadataFilter(key="type", value="desc"))
            search_filters_desc = MetadataFilters(filters=filters_desc)
            retriever_desc = self._index.as_retriever(filters=search_filters_desc, similarity_top_k=6)
            
            # 3.2 Search for Type=summary_review
            filters_summary = base_filters.copy()
            filters_summary.append(MetadataFilter(key="type", value="summary_review"))
            search_filters_summary = MetadataFilters(filters=filters_summary)
            retriever_summary = self._index.as_retriever(filters=search_filters_summary, similarity_top_k=6)

            for q in queries_to_run:
                try:
                    # Run both searches
                    res_desc = retriever_desc.retrieve(q)
                    res_summ = retriever_summary.retrieve(q)
                    all_nodes.extend(res_desc)
                    all_nodes.extend(res_summ)
                except Exception as e:
                    print(f"Error searching for '{q}': {e}")
            
            # 4. Deduplication
            unique_nodes = self._deduplicate_nodes(all_nodes)
            print(f"Deduplication (Split Search): {len(all_nodes)} -> {len(unique_nodes)} unique nodes")

            # 5. Reranking using LLM
            nodes = self._rerank_nodes(query_str, unique_nodes, top_n=TOP_K_RERANK)

        # ---------------------------------------------------------
        # 4. CATEGORY SEARCH (SQL ONLY)
        # ---------------------------------------------------------
        elif category == QueryCategory.CATEGORY_SEARCH:
            # Strict SQL search based on Extracted Filters
            conn = get_db_connection()
            if conn:
                try:
                    cur = conn.cursor()
                    rows = []
                    
                    if filters_data.faculty:
                        print(f"Category Search: Faculty = {filters_data.faculty}")
                        cur.execute("""
                            SELECT course_id, course_name_th, credits, description 
                            FROM courses 
                            WHERE faculty = %s LIMIT 80
                        """, (filters_data.faculty,))
                        rows = cur.fetchall()
                        header = f"รายวิชาใน {filters_data.faculty}:\n"

                    elif filters_data.category:
                         print(f"Category Search: Category = {filters_data.category}")
                         cur.execute("""
                            SELECT course_id, course_name_th, credits, description 
                            FROM courses 
                            WHERE category_64 = %s LIMIT 80
                        """, (filters_data.category,))
                         rows = cur.fetchall()
                         header = f"รายวิชาในหมวด {filters_data.category}:\n"
                    
                    if rows:
                        list_text = header
                        for r in rows:
                            cid, cname, cred, desc = r
                            list_text += f"- **{cid}** {cname} [{cred} หน่วยกิต]\n\n"
                            # list_text += f"- **{cid}** {cname} [{cred} หน่วยกิต]\n คำอธิบาย: {desc}\n"
                        
                        node = TextNode(text=list_text)
                        nodes = [NodeWithScore(node=node, score=1.0)]
                    else:
                        # Return empty if logic fails, let Synthesizer handle "No data"
                        pass

                    cur.close()
                    conn.close()
                except Exception as e:
                    print(f"SQL Error in CategorySearch: {e}")
        
        # ---------------------------------------------------------
        # 5. CHIT CHAT / UNCLEAR (Return Empty)
        # ---------------------------------------------------------
        else:
            nodes = []

        return nodes
