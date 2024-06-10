#!/bin/bash

export AWS_REGION=eu-west-3
export STACK_NAME=osstest2

# Time period for the main page scrape lambda repetition:
export CYCLE_PERIOD_VALUE=2
export CYCLE_PERIOD_UNIT=minute

export LOG_LEVEL='DEBUG'

##################################################################

# Prevent terminal output waiting:
export AWS_PAGER=""

source stack.sh $STACK_NAME create \
"timePeriodValue=$CYCLE_PERIOD_VALUE \
timePeriodUnit=$CYCLE_PERIOD_UNIT"

# Add environment variables to the lambdas
aws lambda update-function-configuration \
--function-name $MAIN_FUNCTION_NAME \
--environment "Variables={LOG_LEVEL=$LOG_LEVEL}" &> /dev/null

aws lambda update-function-configuration \
--function-name $NEWS_FUNCTION_NAME \
--environment "Variables={LOG_LEVEL=$LOG_LEVEL, \
AWS_REGION=$AWS_REGION}" &> /dev/null

# Now enable the periodic lambda, preserving the other parameters
NEW_SCHEDULE_FILE=new_sched_temp.json
aws scheduler get-schedule \
--name $STACK_NAME-schedule | \
python3 -c \
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
