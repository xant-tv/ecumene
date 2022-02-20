#!/bin/bash

# Teardown container network
docker-compose -f docker-compose.yml down -v
docker stop ecumene-bot && docker rm ecumene-bot