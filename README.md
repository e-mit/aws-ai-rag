# AWS AI RAG


![tests](https://github.com/e-mit/aws-ai-rag/actions/workflows/tests.yml/badge.svg)
![coverage](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/e-mit/9df92671b4e2859b1e75cf762121b73f/raw/aws-ai-rag.json)
![flake8](https://github.com/e-mit/aws-ai-rag/actions/workflows/flake8.yml/badge.svg)
![mypy](https://github.com/e-mit/aws-ai-rag/actions/workflows/mypy.yml/badge.svg)
![pycodestyle](https://github.com/e-mit/aws-ai-rag/actions/workflows/pycodestyle.yml/badge.svg)
![pydocstyle](https://github.com/e-mit/aws-ai-rag/actions/workflows/pydocstyle.yml/badge.svg)
![pylint](https://github.com/e-mit/aws-ai-rag/actions/workflows/pylint.yml/badge.svg)
![pyright](https://github.com/e-mit/aws-ai-rag/actions/workflows/pyright.yml/badge.svg)
![bandit](https://github.com/e-mit/aws-ai-rag/actions/workflows/bandit.yml/badge.svg)


Using RAG (Retrieval-augmented generation) to provide an LLM with up-to-date news.

[Try the working demonstration.](https://mtest.dev)


## Architecture summary

### Main technologies/products used:
- Amazon OpenSearch Service (free tier on t2.small.search with 10GB EBS storage)
- AWS Bedrock generative AI (Anthropic Claude 3 Sonnet) and vector embedding (Titan)
- AWS Lambda, SQS, API Gateway, S3, EventBridge, CloudFormation, DynamoDB
- FastAPI, Mangum


### Data ingestion pipeline

1. A periodically triggered lambda function obtains the URLs of the ten "most read" news articles from the main BBC news website [https://www.bbc.co.uk/news](https://www.bbc.co.uk/news) and places each URL as a message in a SQS queue.
2. A second lambda removes URLs from the queue and does the following steps:
    - Check the OpenSearch vector database and discard the URL if it has already been processed
    - Extract the news article's full text and other information such as publication date, keywords, etc.
    - Form a short text chunk comprising the article title and first 3 paragraphs
    - Produce a vector embedding of the text chunk using the AWS Bedrock Titan model
    - Store the article data as a document in the OpenSearch database, indexed by the embedding vector
3. A third lambda periodically deletes old documents from the OpenSearch database.


### Query process with RAG

1. Serve a simple static website to the user from S3
2. The user sends a question in a REST POST request to the API Gateway, which is routed to a lambda
3. Produce a vector embedding of the question using AWS Bedrock
4. Do a semantic similarity search on the OpenSearch vector database using the vector embedding
5. Combine the full text of the most relevant search results with the question to produce a RAG query
6. Pass the RAG query to the AWS Bedrock Titan LLM and obtain a response
7. Present the response to the user, together with the URLs of the source news articles selected in step 4 as citations/further reading.


### Front end

[github.com/e-mit/aws-api-website](https://github.com/e-mit/aws-api-website) is used to create an API Gateway which serves the files in ```/static/``` and proxies the API.

This also configures a custom domain name for the gateway URL and provides CAPTCHA support.


## Setup notes

- AWS Bedrock is available in only a subset of AWS regions (e.g. Paris, not London)
- Must enable account access to the LLMs ("Foundation Models") with Bedrock before use
