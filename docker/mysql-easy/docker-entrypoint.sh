#!/usr/bin/env bash
set -o errexit
base=/usr/lib/orthanc

# call setup.sh on each setup procedure script found in $base/setup.d (one for each plugin).
find "$base/setup.d" -type f -exec "$base/setup.sh" "{}" ";"

if [[ $TRACE_ENABLED == true ]]; then
	verbosity=--trace
elif [[ $VERBOSE_ENABLED == true ]]; then
	verbosity=--verbose
fi
argv=(strace Orthanc $verbosity "$@")
echo "Startup command: ${argv[*]}" >&2
exec "${argv[@]}"
