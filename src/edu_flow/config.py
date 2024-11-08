import os

# LLM_CONFIG = {
#     "model": "gpt-4o-mini",
#     "api_key": os.getenv('OPENAI_API_KEY')
# }

LLM_CONFIG = {
    "model": "groq/llama3-groq-70b-8192-tool-use-preview",
    "api_key": os.getenv('GROQ_API_KEY')
}

# LLM_CONFIG = {
#     "model": "anthropic/claude-3-5-sonnet-20240620",
#     "api_key": os.getenv('ANTHROPIC_API_KEY')
# }

EDU_FLOW_INPUT_VARIABLES = {
    "audience_level": "beginner",
    "topic": "Generative AI"
} 