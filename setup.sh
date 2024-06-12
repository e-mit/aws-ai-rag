#!/bin/bash

# Run this script to deploy the project on AWS

export AWS_REGION=eu-west-3
export STACK_NAME=osstest2

# Time period for the main page scrape lambda repetition:
export CYCLE_PERIOD_VALUE=4
export CYCLE_PERIOD_UNIT=hour

export LOG_LEVEL='DEBUG'

##################################################################

# Prevent terminal output waiting:
export AWS_PAGER=""

source stack.sh $STACK_NAME create \
"timePeriodValue=$CYCLE_PERIOD_VALUE \
timePeriodUnit=$CYCLE_PERIOD_UNIT \
logLevel=$LOG_LEVEL"


export OSS_NODE_URL='https://'$(aws opensearch describe-domain \
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
    echo "The OpenSearch endpoint URL is $OSS_NODE_URL"
    python create_oss_index.py
fi
