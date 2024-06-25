#!/bin/bash
# Run tests, coverage and linters. Uses a local containerised dynamoDB instance.

export DB_TABLE_NAME=testTable
export TEST=true
export QUERY_LAMBDA_ARN=test
export AWS_REGION=eu-west-3
export API_STAGE_NAME=v1

# Prevent terminal output waiting:
export AWS_PAGER=""

source auth_dev.sh

docker run --rm --name dynamodb_test_local -d -p 8000:8000 amazon/dynamodb-local
sleep 5
./create_test_db_table.sh

# enable printing:
#pytest -v -s tests

python -m pytest --cov=. tests -p no:cacheprovider

docker stop -t 0 dynamodb_test_local

python -m bandit -r . --exclude=/tests/,/venv/,/old_examples/,/layer/
python -m flake8 --exclude=tests/*,venv/*,layer/*,old_examples/*
python -m mypy . --explicit-package-bases --exclude 'tests/' --exclude 'venv/' --exclude 'layer/' --exclude 'old_examples/'
python -m pycodestyle *.py fastapi_lambda main_scrape_lambda news_scrape_lambda query_lambda
python -m pydocstyle *.py fastapi_lambda main_scrape_lambda news_scrape_lambda query_lambda --ignore=D107,D203,D213
python -m pylint *.py fastapi_lambda main_scrape_lambda news_scrape_lambda query_lambda
python -m pyright *.py fastapi_lambda main_scrape_lambda news_scrape_lambda query_lambda
