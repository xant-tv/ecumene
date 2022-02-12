#!/bin/bash

# Reloads nginx in the container to recognise new cert
docker exec -it ecumene-nginx nginx -s reload