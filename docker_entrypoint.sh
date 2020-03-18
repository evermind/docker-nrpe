#!/bin/bash

set -e

/usr/local/bin/update_config.py /etc/nrpe.cfg

echo "Starting nrpe daemon (allowed hosts: ${ALLOWED_HOSTS})"

syslogd -n -O- &

if [ "${SSL_ENABLED}" == "true" ]; then
  nrpe -c /etc/nrpe.cfg -f
else
  nrpe -c /etc/nrpe.cfg -f -n
fi
