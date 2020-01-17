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

# default type is duckiebot
if [ -z ${ROBOT_TYPE+x} ]; then
  echo "The environment variable ROBOT_TYPE is required. Exiting.";
  exit 1;
fi

# launching app
dt_exec python3 -m system_monitor --verbose --type ${ROBOT_TYPE} --duration ${DURATION}


# ----------------------------------------------------------------------------
# YOUR CODE ABOVE THIS LINE

# terminate launch file
dt_launchfile_terminate
