#! /bin/bash

exec gunicorn -b 0.0.0.0:5100 --worker-tmp-dir /dev/shm --workers=2 --threads=4 --worker-class=gthread -t 120 wsgi:app