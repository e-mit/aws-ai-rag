# Use the native inference API to send a text message to Amazon Titan Text.
import json
from pprint import pprint
from typing import Any
from datetime import datetime, timedelta

import boto3
from botocore.exceptions import ClientError


# Create a Bedrock Runtime client in the AWS Region of your choice.
client = boto3.client("bedrock-runtime", region_name="eu-west-3")

# Set the model ID
#model_id = "amazon.titan-text-lite-v1"
model_id = "anthropic.claude-3-sonnet-20240229-v1:0"

# Define the prompt for the model.
#prompt = """Describe the purpose of a 'hello world' program."""
query = 'What happened yesterday?'
today = '12 June 2024'
prompt = (f"Today is {today}. Given the following query, what"
          " date or dates are relevant when searching a database"
          " of news articles? Return only the date(s), as a Python array of strings. Answer"
          " 'None' if no dates are relevant."
          f" Query: '{query}'")

today = datetime.now().strftime('%d %B %Y')
earliest = (datetime.now() - timedelta(days=7)).strftime('%d %B %Y')
query = 'What happened in the USA yesterday?'
prompt = (f"Does the following query relate to news events"
          f" which happened after {earliest}? The date today is {today}. Answer"
          f" yes or no and explain why. Do not return any other text. Query: '{query}'")

# Format the request payload using the model's native structure.
if "titan" in model_id:
    native_request = {
        "inputText": prompt,
        "textGenerationConfig": {
            "maxTokenCount": 512,  # limits response by just cutting it off
            "temperature": 0.5,  # 0-1: 0 = deterministic, 1 = creative/random
            "topP": 0.5  # 0-1: 0 = ignore less probable options (less diverse)
        },
    }
elif "claude" in model_id:
    native_request: dict[str, Any] = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 1.0,
            "top_p": 0.999,
            "top_k": 250
        }

# Convert the native request to JSON string.
request = json.dumps(native_request)

try:
    # Invoke the model with the request.
    response = client.invoke_model(modelId=model_id, body=request)

except (ClientError, Exception) as e:
    print(f"ERROR: Can't invoke '{model_id}'. Reason: {e}")
    exit(1)

# Decode the response body.
model_response = json.loads(response["body"].read())

# Extract and print the response text.
if "titan" in model_id:
    response_text = model_response["results"][0]["outputText"]
elif "claude" in model_id:
    response_text = model_response["content"][0]["text"]

print(response_text)
print()
pprint(model_response)
