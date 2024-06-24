#!/bin/bash

# Run this script to deploy the project on AWS

export AWS_REGION=eu-west-3
export STACK_NAME=osstest6
export API_STAGE_NAME=v1

# Time period for the main page scrape lambda repetition:
export CYCLE_PERIOD_VALUE=4
export CYCLE_PERIOD_UNIT=hour

export LOG_LEVEL=DEBUG

# Choose the OpenSearch database index name: must be lower case
export OSS_INDEX_NAME=news

# Define the website login credentials (bcrypt hash):
AUTH_USER_PASSWORD_HASH='$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW'
AUTH_ADMIN_PASSWORD_HASH='$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW'

##################################################################

# Prevent terminal output waiting:
export AWS_PAGER=""

source stack.sh $STACK_NAME create \
"timePeriodValue=$CYCLE_PERIOD_VALUE \
timePeriodUnit=$CYCLE_PERIOD_UNIT \
logLevel=$LOG_LEVEL"


# Create the OpenSearch service index
export OPENSEARCH_URL='https://'$(aws opensearch describe-domain \
--domain-name $STACK_NAME-oss-domain | \
python3 -c \
"import sys, json
try:
    print(json.load(sys.stdin)['DomainStatus']['Endpoint'])
except:
    exit(1)")
if [[ "$?" -ne 0 ]]; then
    echo "Error: could not obtain the OpenSearch endpoint URL"
else
    echo "The OpenSearch endpoint URL is $OPENSEARCH_URL"
    python create_oss_index.py
fi


# Supply environment variables to fastapi lambda:
ENV_VARS=$(aws lambda get-function-configuration \
    --function-name ${STACK_NAME}-fastapi_lambda | python3 -c \
"import sys, json
environment = json.load(sys.stdin)['Environment']
environment['Variables']['AUTH_SECRET_KEY'] = '$(openssl rand -hex 32)'
environment['Variables']['AUTH_USER_PASSWORD_HASH'] = '$AUTH_USER_PASSWORD_HASH'
environment['Variables']['AUTH_ADMIN_PASSWORD_HASH'] = '$AUTH_ADMIN_PASSWORD_HASH'
environment['Variables']['API_STAGE_NAME'] = '$API_STAGE_NAME'
print(json.dumps(environment))")
aws lambda update-function-configuration \
    --function-name ${STACK_NAME}-fastapi_lambda \
    --environment "$ENV_VARS" &> /dev/null

# Supply environment variables to query lambda:
ENV_VARS=$(aws lambda get-function-configuration \
    --function-name ${STACK_NAME}-query_lambda | python3 -c \
"import sys, json
environment = json.load(sys.stdin)['Environment']
environment['Variables']['OSS_INDEX_NAME'] = '$OSS_INDEX_NAME'
print(json.dumps(environment))")
aws lambda update-function-configuration \
    --function-name ${STACK_NAME}-query_lambda \
    --environment "$ENV_VARS" &> /dev/null

# Now enable the web scraping lambda's schedule, preserving the other parameters
NEW_SCHEDULE_FILE=new_sched_temp.json
aws scheduler get-schedule \
    --name $STACK_NAME-schedule | python3 -c \
"import sys, json
try:
    sched = json.load(sys.stdin)
    new_sched = {'State': 'ENABLED'}
    for k in ['FlexibleTimeWindow','ScheduleExpression','Target','Name']:
        new_sched[k] = sched[k]
    print(json.dumps(new_sched))
except Exception:
    pass
" > $NEW_SCHEDULE_FILE
aws scheduler update-schedule \
    --cli-input-json file://$NEW_SCHEDULE_FILE &> /dev/null
rm -f $NEW_SCHEDULE_FILE

# Get the API lambda ARN:
AWS_AC_ID=$(aws sts get-caller-identity --query Account --output text)
export API_LAMBDA_ARN="arn:aws:lambda:${AWS_REGION}:${AWS_AC_ID}:function:${STACK_NAME}-fastapi_lambda"
echo ""
echo "The API Lambda ARN is $API_LAMBDA_ARN"
echo ""
