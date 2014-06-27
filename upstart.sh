#!/bin/bash
set -e

# logfile and location
LOGFILE=/var/log/django/microweb.log
LOGDIR=$(dirname $LOGFILE)

# number of gunicorn workers
NUM_WORKERS=17
HOST='127.0.0.1:8000'

# user/group to run as
USER=django
GROUP=microcosm

# activate virtualenv
source /srv/www/django/microwebenv/bin/activate

cd /srv/www/django/microweb
test -d $LOGDIR || mkdir -p $LOGDIR

NEW_RELIC_CONFIG_FILE=/srv/www/django/microweb/newrelic.ini
export NEW_RELIC_CONFIG_FILE

exec /srv/www/django/microwebenv/bin/newrelic-admin run-program \
  /srv/www/django/microwebenv/bin/gunicorn_django -b $HOST \
  -w $NUM_WORKERS -k gevent --user=$USER --group=$GROUP --log-level=info \
  --max-requests 5000 --log-file=$LOGFILE 2>>$LOGFILE
