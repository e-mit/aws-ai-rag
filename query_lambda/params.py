"""Parameters for the OpenSearch service and LLM GenAI."""

EMBEDDING_MODEL_ID = "amazon.titan-embed-image-v1"
EMBEDDING_MODEL_DIM = 1024

# Search result selection parameters:
QUERY_SIZE = 3
QUERY_K = 3
SCORE_THRESHOLD = 0.1
EXPIRY_PERIOD_DAYS = 8
INDEX_NAME = "news"
HIT_LIMIT = 6

# LLM parameters:
LLM_MODEL_ID = "anthropic.claude-3-sonnet-20240229-v1:0"
TEMPERATURE = 0.5
TOP_P = 0.999
TOP_K = 250
MAX_OUTPUT_TOKENS = 1000

# Responses
INAPPROPRIATE_REPLY = "Please ask a question which relates to the news."
NO_RESULTS_REPLY = "Sorry, I couldn't find any relevant news articles."
