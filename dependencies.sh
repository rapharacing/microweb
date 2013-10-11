#!/bin/bash

sudo apt-get -y install libevent1-dev libmemcached-dev

virtualenv ENV
source ENV/bin/activate
pip install -r requirements.txt
deactivate
