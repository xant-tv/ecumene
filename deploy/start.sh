#!/bin/bash

# Make sure remote images are pulled
# TODO: Use environment for image host and tags
docker pull ghcr.io/xant-tv/ecumene/ecumene-core:latest
docker pull ghcr.io/xant-tv/ecumene/ecumene-nginx:latest

# Compose command to deploy on remote host
docker-compose -f docker-compose.yml up -d --no-build
docker run -d -v "/opt/oracle/network/admin:/opt/oracle/network/admin" --env-file .env --name ecumene-bot ghcr.io/xant-tv/ecumene/ecumene-core:latest bot