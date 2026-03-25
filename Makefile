.PHONY: help swag-fmt dev db-reset release docker-login setup-buildx clean

# Configuration
GH_USER ?= $(GITHUB_USERNAME)
REGISTRY := ghcr.io
IMAGE_NAME := $(REGISTRY)/$(GH_USER)/garmin-health-to-sfs
DOCKER_DIR := ./docker
DOCKER_COMPOSE := docker compose -f $(DOCKER_DIR)/docker-compose.yml

# Get version from git or default
VERSION ?= $(shell git describe --tags --always --dirty 2>/dev/null || echo "v0.0.0-dev")

# Export additional local dev env details
SHELL := /bin/bash
	export
	include docker/.env.local

help:
	@echo "garmin-health-to-sfs Management"
	@echo "  make release      - Prompt for version and push universal images to GHCR"


# --- Production & Release ---

docker-login:
	@echo "🔑 Logging into GHCR..."
	@echo "$(GITHUB_TOKEN)" | docker login $(REGISTRY) -u $(GH_USER) --password-stdin

setup-buildx:
	@if ! docker buildx inspect ghtsfs-builder > /dev/null 2>&1; then \
		echo "🔧 Creating new buildx builder..."; \
		docker buildx create --name ghtsfs-builder --driver docker-container --use; \
	else \
		echo "✅ Using existing buildx builder..."; \
		docker buildx use ghtsfs-builder; \
	fi
	@docker buildx inspect --bootstrap

release: setup-buildx docker-login
	@read -p "Enter version tag (e.g., v1.0.1): " REL_VER; \
	echo "🌎 Building and pushing universal images for $$REL_VER..."; \
	docker buildx build \
		--platform linux/amd64,linux/arm64 \
		--provenance=false \
		--build-arg VERSION=$$REL_VER \
		-t $(IMAGE_NAME):$$REL_VER \
		-t $(IMAGE_NAME):latest \
		-f $(DOCKER_DIR)/Dockerfile \
		--push .
	@echo "✅ Release pushed successfully!"
