#!/bin/bash

source /environment.sh

# initialize launch file
dt_launchfile_init

# YOUR CODE BELOW THIS LINE
# ----------------------------------------------------------------------------


# NOTE: Use the variable CODE_DIR to know the absolute path to your code
# NOTE: Use `dt_exec COMMAND` to run the main process (blocking process)

# default timeout value is 10 minutes
if [ -z ${DURATION+x} ]; then
  DURATION=600;
fi

# ROBOT_TYPE is mandatory
if [ -z ${ROBOT_TYPE+x} ]; then
  echo "The environment variable ROBOT_TYPE is required. Exiting.";
  exit 1;
fi

# LOG_GROUP is mandatory
if [ -z ${LOG_GROUP+x} ]; then
  echo "The environment variable LOG_GROUP is required. Exiting.";
  exit 2;
fi

# LOG_API_APP_ID is mandatory
if [ -z ${LOG_API_APP_ID+x} ]; then
  LOG_API_APP_ID="101741598378777739147_distro_comparison_1";
#  echo "The environment variable LOG_API_APP_ID is required. Exiting.";
#  exit 3;
fi

# LOG_API_APP_SECRET is mandatory
if [ -z ${LOG_API_APP_SECRET+x} ]; then
  LOG_API_APP_SECRET="PgFrcD6msrenk5VuAJqryMSI58z4OpBuw6LyAIKS0P6aKSvb";
#  echo "The environment variable LOG_API_APP_SECRET is required. Exiting.";
#  exit 4;
fi

# DEBUG is optional
if [ "${DEBUG}" = "1" ]; then
  DEBUG_ARG='--debug';
fi


# launching app
dt_exec python3 \
  -m system_monitor \
    --verbose \
    ${DEBUG_ARG} \
    --type ${ROBOT_TYPE} \
    --app-id ${LOG_API_APP_ID} \
    --app-secret ${LOG_API_APP_SECRET} \
    --group ${LOG_GROUP} \
    --duration ${DURATION}

# ----------------------------------------------------------------------------
# YOUR CODE ABOVE THIS LINE

# terminate launch file
dt_launchfile_terminate
