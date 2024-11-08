import os

# Configuration for LLM
LLM_CONFIG = {
    "model": "gpt-4o-mini",
    "api_key": os.getenv('OPENAI_API_KEY')
}

# Configuration for EduFlow
EDU_FLOW_INPUT_VARIABLES = {
    "audience_level": "beginner",
    "topic": "Generative AI"
} 