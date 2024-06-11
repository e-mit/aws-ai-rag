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
timePeriodUnit=$CYCLE_PERIOD_UNIT \
logLevel=$LOG_LEVEL"
