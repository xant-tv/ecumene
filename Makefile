SHELL=/bin/bash

.PHONY: build-web
build-web: ## Builds Ecumene webserver
	docker build \
	--no-cache \
	-f Dockerfile.web \
	-t ecumene-web:dev .

.PHONY: run-web
run-web: build-web ## Runs the Ecumene webserver
	docker run ecumene-web:dev