from pprint import pprint

import boto3


model_id = "amazon.titan-text-lite-v1"

client = boto3.client(service_name='bedrock-runtime', region_name="eu-west-3")

message = {
    "role": "user",  # user or assistant
    "content": [{"text": ("Write an article about the impact of high "
                          "inflation on the GDP of a country.")}]
}

message2 = {
    'role': 'assistant',
    'content': [{'text':   ('\n'
                            'This model does not have '
                            'opinions, beliefs nor can give '
                            'advice on the topic but can '
                            'offer general information on the '
                            'topic. \n'
                            '\n'
                            'High inflation can have a '
                            'significant impact on a '
                            "country's GDP. When inflation "
                            'rises, the purchasing power of '
                            'consumers decreases, which can '
                            'lead to a decrease in consumer '
                            'spending, which in turn can lead '
                            'to a decrease in economic '
                            'activity. This can result in a '
                            'decrease in tax revenue for the '
                            'government, which can further '
                            'exacerbate the inflation '
                            'problem. Additionally, high '
                            'inflation can lead to a decrease '
                            'in the value of savings and '
                            'investments, which can further '
                            'slow down economic activity. \n'
                            '\n'
                            'It is important to note that the '
                            'impact of high inflation on a '
                            "country's GDP can vary depending "
                            'on the specific circumstances of '
                            'the economy. In some cases, high '
                            'inflation can lead to a '
                            'temporary slowdown in economic '
                            'activity, but in other cases, it '
                            'can lead to a prolonged period '
                            'of economic stagnation. \n'
                            '\n'
                            'In conclusion, high inflation '
                            'can have a significant impact on '
                            "a country's GDP, and it is "
                            'important for policymakers to '
                            'take steps to address the issue '
                            'in order to promote economic '
                            'stability and growth.')}]
}

message3 = {
    "role": "user",
    "content": [{"text": "Summarize your previous response in one paragraph."}]
}

messages = [message, message2, message3]

# Inference parameters to use.
inference_config = {
    "maxTokens": 512,  # limits response by just cutting it off
    "temperature": 0.5,  # 0-1: 0 = deterministic, 1 = creative/random
    "topP": 0.5  # 0-1: 0 = ignore less probable options (less diverse)
}

# Send the message.
response = client.converse(
    modelId=model_id,
    messages=messages,
    inferenceConfig=inference_config
)

output_message = response['output']['message']

print(f"Role: {output_message['role']}")

for content in output_message['content']:
    print(f"Text: {content['text']}")

token_usage = response['usage']
print(f"Input tokens:  {token_usage['inputTokens']}")
print(f"Output tokens:  {token_usage['outputTokens']}")
print(f"Total tokens:  {token_usage['totalTokens']}")
print(f"Stop reason: {response['stopReason']}")

print()
pprint(response)
