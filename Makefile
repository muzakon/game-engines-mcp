include .env
export

IMAGE_NAME  := game-engine-mcp
IMAGE_TAG   := latest

.PHONY: build run stop index

build:
	docker build --build-arg UNITY_MCP_PORT=$(UNITY_MCP_PORT) \
		-t $(IMAGE_NAME):$(IMAGE_TAG) .

run:
	docker run -d --name $(IMAGE_NAME) \
		--env-file .env \
		-p $(UNITY_MCP_PORT):$(UNITY_MCP_PORT) \
		$(IMAGE_NAME):$(IMAGE_TAG)

stop:
	docker stop $(IMAGE_NAME) 2>/dev/null || true
	docker rm $(IMAGE_NAME) 2>/dev/null || true

up: stop build run

restart: stop run

index:
	uv run python scripts/build_index.py

reindex:
	uv run python scripts/build_index.py -v

logs:
	docker logs -f $(IMAGE_NAME)
