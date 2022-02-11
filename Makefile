SHELL=/bin/bash

.PHONY: build-web
build-web: ## Builds Ecumene webserver
	docker build \
	--build-arg MODULE=web \
	--file Dockerfile \
	--tag ecumene-web:dev \
	.

.PHONY: run-web
run-web: build-web ## Runs the Ecumene webserver
	docker run ecumene-web:dev

.PHONY: build-bot
build-bot: ## Builds Ecumene Discord bot
	docker build \
	--build-arg MODULE=bot \
	--file Dockerfile \
	--tag ecumene-bot:dev \
	.

.PHONY: run-bot
run-bot: build-bot ## Runs the Ecumene Discord bot
	docker run ecumene-bot:dev