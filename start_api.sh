#!/bin/bash
# Wrapper script for Dojobay API startup
set -e

cd /root/dojobay
source venv/bin/activate
export $(cat .env.production | xargs)

exec python -m gunicorn \
    -c gunicorn_external_api_prod.conf.py \
    --access-logfile /root/dojobay/external_api_access.log \
    --error-logfile /root/dojobay/external_api_error.log \
    external_api:app
