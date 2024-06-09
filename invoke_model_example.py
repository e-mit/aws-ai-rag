# Use the native inference API to send a text message to Amazon Titan Text.
import json
from pprint import pprint

import boto3
from botocore.exceptions import ClientError


# Create a Bedrock Runtime client in the AWS Region of your choice.
client = boto3.client("bedrock-runtime", region_name="eu-west-3")

# Set the model ID
model_id = "amazon.titan-text-lite-v1"

# Define the prompt for the model.
prompt = """Describe the purpose of a 'hello world' program."""

# Format the request payload using the model's native structure.
native_request = {
    "inputText": prompt,
    "textGenerationConfig": {
        "maxTokenCount": 512,  # limits response by just cutting it off
        "temperature": 0.5,  # 0-1: 0 = deterministic, 1 = creative/random
        "topP": 0.5  # 0-1: 0 = ignore less probable options (less diverse)
    },
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
response_text = model_response["results"][0]["outputText"]
print(response_text)
print()
pprint(model_response)
