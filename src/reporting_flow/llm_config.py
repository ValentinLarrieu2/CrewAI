from crewai import LLM
from .config import LLM_CONFIG

# Use more capable model for better delegation handling in hierarchical mode
# If the default model is gpt-4o-mini, we're upgrading to gpt-4o for better delegation support
llm = LLM(
    model=LLM_CONFIG.get("model", "gpt-4o-mini"),  # Default to gpt-4o if not specified
    api_key=LLM_CONFIG["api_key"]
) 