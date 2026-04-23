include .env
export

IMAGE_NAME  := game-engine-mcp
IMAGE_TAG   := latest

.PHONY: build run stop index reindex logs release release-all

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

# --- GitHub Release helpers ---
# Set GITHUB_TOKEN before running (needs repo scope).
#   export GITHUB_TOKEN=ghp_...

# Upload a single docset: make release ENGINE=godot VERSION=4.6 DOCSET=reference
release:
	@uv run python -c '\
import gzip, json, os, subprocess, sys; \
sys.path.insert(0, "src"); \
from src.config import DATA_DIR; \
from src.downloader import load_config; \
cfg = load_config(); \
tag = "$(ENGINE)-$(VERSION)-$(DOCSET)"; \
db = DATA_DIR / "$(ENGINE)" / "$(VERSION)" / "$(DOCSET).db"; \
gz = db.with_suffix(".db.gz"); \
assert db.exists(), f"DB not found: {db}"; \
print(f"Compressing {db} ..."); \
gzip.open(gz, "wb").writelines(open(db, "rb")); \
print(f"Uploading {tag} ({gz.stat().st_size/1e6:.1f} MB) ..."); \
token = os.environ["GITHUB_TOKEN"]; \
api = f"https://api.github.com/repos/{cfg.release.owner}/{cfg.release.repo}/releases/tags/{tag}"; \
r = subprocess.run(["curl","-s","-f","-H",f"Authorization: token {token}","-H","Accept: application/vnd.github+json",api], capture_output=True, text=True); \
rid = json.loads(r.stdout)["id"] if r.returncode == 0 else None; \
rid = rid or json.loads(subprocess.run(["curl","-s","-f","-H",f"Authorization: token {token}","-H","Accept: application/vnd.github+json","-X","POST","-d",json.dumps({"tag_name":tag,"name":tag,"body":f"Pre-built index for $(ENGINE) $(VERSION) $(DOCSET)"}),f"https://api.github.com/repos/{cfg.release.owner}/{cfg.release.repo}/releases"], capture_output=True, text=True).stdout)["id"]; \
subprocess.run(["curl","-s","-f","-H",f"Authorization: token {token}","-H","Content-Type: application/gzip","-X","POST","--data-binary",f"@{gz}",f"https://uploads.github.com/repos/{cfg.release.owner}/{cfg.release.repo}/releases/{rid}/assets?name={gz.name}"], check=True); \
gz.unlink(missing_ok=True); \
print(f"Done: {tag}")'

# Release all configured docsets at once
release-all:
	@uv run python scripts/release_all.py
