from core.config import (
    token_counter_main, token_counter_rewrite, token_counter_rerank
)

def reset_all_counters():
    """Resets all global token counters."""
    token_counter_main.reset_counts()
    token_counter_rewrite.reset_counts()
    token_counter_rerank.reset_counts()

def print_performance_report(response):
    """
    Prints a detailed performance report to the terminal,
    including latency breakdown and token usage per model.
    """
    # Calculate Totals
    total_prompt = (
        token_counter_main.prompt_llm_token_count + 
        token_counter_rewrite.prompt_llm_token_count + 
        token_counter_rerank.prompt_llm_token_count
    )
    total_completion = (
        token_counter_main.completion_llm_token_count + 
        token_counter_rewrite.completion_llm_token_count + 
        token_counter_rerank.completion_llm_token_count
    )
    
    # Get latency data safely
    latency = response.metadata.get("latency_breakdown", {})
    t_total = latency.get("total_engine", 0.0)
    t_route = latency.get("routing", 0.0)
    t_resol = latency.get("resolution", 0.0)
    t_retr  = latency.get("retrieval", 0.0)
    t_rerank= latency.get("rerank", 0.0)
    t_synth = latency.get("synthesis", 0.0)

    # Print Performance Report
    print("\n" + "="*40)
    print("Performance Report (Detailed)")
    print("="*40)
    print(f"  Total Time:   {t_total:.4f}s")
    print(f"   - Routing:    {t_route:.4f}s")
    print(f"   - Resolution: {t_resol:.4f}s")
    print(f"   - Retrieval:  {t_retr:.4f}s")
    print(f"   - Rerank:     {t_rerank:.4f}s")
    print(f"   - Synthesis:  {t_synth:.4f}s")
    print("-" * 40)
    print(f" Total Tokens: {total_prompt + total_completion}")
    print(f"   (Prompt: {total_prompt}, Completion: {total_completion})")
    print("-" * 40)
    print(" Breakdown by Model:")
    print(f"   1. Router (Rewrite LLM): {token_counter_rewrite.total_llm_token_count} tokens")
    print(f"      (P: {token_counter_rewrite.prompt_llm_token_count}, C: {token_counter_rewrite.completion_llm_token_count})")
    print(f"   2. Reranker (Rerank LLM): {token_counter_rerank.total_llm_token_count} tokens")
    print(f"      (P: {token_counter_rerank.prompt_llm_token_count}, C: {token_counter_rerank.completion_llm_token_count})")
    print(f"   3. Synthesis (Main LLM): {token_counter_main.total_llm_token_count} tokens")
    print(f"      (P: {token_counter_main.prompt_llm_token_count}, C: {token_counter_main.completion_llm_token_count})")
    print("="*40 + "\n")
