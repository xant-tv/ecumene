#!/bin/bash

# Case based on module variable.
# This should have been set during container build.
case "$1" in
    "bot")
        python main.py bot
        ;;
    "web")
        gunicorn \
            --config conf/gunicorn.py \
            --bind 0.0.0.0:8080 \
            --workers 5 \
            web.app:client
        ;;
    "task")
        python main.py task
        ;;
    *)
        echo "Module not specified!"
        ;;
esac