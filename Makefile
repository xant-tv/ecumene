SHELL=/bin/bash

.PHONY: build
build: build-core build-nginx

## Builds core Ecumene container
.PHONY: build-core
build-core: 
    docker build \
    --file src/Dockerfile \
    --tag ecumene-core:dev \
    src

## Builds external proxy container
.PHONY: build-nginx
build-nginx:
    docker build \
    --file nginx/Dockerfile \
    --tag ecumene-nginx:dev \
    nginx

## Runs core as webserver
.PHONY: run-web
run-web: build-core 
    docker run \
    -p 8080:8080 \
    --env-file .env \
    --name ecumene-web \
    ecumene-core:dev \
    "web"

## Runs core as Discord bot
.PHONY: run-bot
run-bot: build-core
    docker run \
    --env-file .env \
    --name ecumene-bot \
    ecumene-core:dev \
    "bot"

## Runs core as task scheduler
.PHONY: run-task
run-task: build-core
    docker run \
    --env-file .env \
    --name ecumene-task \
    ecumene-core:dev \
    "task"