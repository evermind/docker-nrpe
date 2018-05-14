#!/bin/bash

set -e

/usr/local/bin/update_config.py /etc/nrpe.cfg

echo "Starting nrpe daemon (allowed hosts: ${ALLOWED_HOSTS})"

#touch /tmp/nrpe.log
#chown nagios /tmp/nrpe.log
#tail -f /tmp/nrpe.log &

syslogd -n -O- &
nrpe -c /etc/nrpe.cfg -f -n
