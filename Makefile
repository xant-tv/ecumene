SHELL=/bin/bash

## Builds core Ecumene container
.PHONY: build
build: 
    docker build \
    --file src/Dockerfile \
    --tag ecumene-core:dev \
    src

## Runs core as webserver
.PHONY: run-web
run-web: build 
    docker run \
    -p 8080:8080 \
    --env-file .env \
    --name ecumene-web \
    ecumene-core:dev \
    "web"

## Runs core as Discord bot
.PHONY: run-bot
run-bot: build 
    docker run \
    --env-file .env \
    --name ecumene-bot \
    ecumene-core:dev \
    "bot"

## Runs core as task scheduler
.PHONY: run-task
run-task: build
    docker run \
    --env-file .env \
    --name ecumene-task \
    ecumene-core:dev \
    "task"