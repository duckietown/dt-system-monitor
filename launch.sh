#!/bin/bash

source /environment.sh

# initialize launch file
dt_launchfile_init

# YOUR CODE BELOW THIS LINE
# ----------------------------------------------------------------------------


# NOTE: Use the variable CODE_DIR to know the absolute path to your code
# NOTE: Use `dt_exec COMMAND` to run the main process (blocking process)

_LAUNCH_ARGS=()

# default timeout value is 10 minutes
if [ -z ${DURATION+x} ]; then
  _LAUNCH_ARGS+=(--duration 600);
fi

# launching app
dt_exec python3 \
  -m system_monitor \
    --verbose \
    "${_LAUNCH_ARGS[@]}" \
    "$@"

# ----------------------------------------------------------------------------
# YOUR CODE ABOVE THIS LINE

# terminate launch file
dt_launchfile_terminate
