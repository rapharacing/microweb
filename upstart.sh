#!/bin/bash
set -e

# logfile and location
LOGFILE=/var/log/gunicorn/microweb.log
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
exec /srv/www/django/microwebenv/bin/gunicorn_django -b $HOST \
  -w $NUM_WORKERS --user=$USER --group=$GROUP --log-level=debug \
  --log-file=$LOGFILE 2>>$LOGFILE
