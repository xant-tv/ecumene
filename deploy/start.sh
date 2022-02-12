#!/bin/bash

# Make sure remote images are pulled
# TODO: Use environment for image host and tags
docker pull ghcr.io/xant-tv/ecumene/ecumene-core:release
docker pull ghcr.io/xant-tv/ecumene/ecumene-nginx:release

# Compose command to deploy on remote host
docker-compose -f docker-compose.yml up -d --no-build