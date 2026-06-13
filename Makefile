.PHONY: run docker-build run-docker

IMAGE := valor-auto-agent
ENV_FILE := $(if $(wildcard .env),--env-file .env,)

# run backend + frontend locally; ctrl-c stops both
run:
	@uv run uvicorn backend.main:app --app-dir src --port 8000 & \
	backend_pid=$$!; \
	trap 'kill $$backend_pid 2>/dev/null' EXIT; \
	uv run streamlit run src/frontend/app.py

docker-build:
	docker build -t $(IMAGE) .

# build the image and run backend + frontend in one container
run-docker: docker-build
	docker run --rm -it $(ENV_FILE) -p 8000:8000 -p 8501:8501 $(IMAGE)
