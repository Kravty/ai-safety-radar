# Development Guide

## When to Restart vs Rebuild

### ✅ RESTART only (fast, ~10 seconds)

Use `podman-compose restart <service>` when changing:
- **Python source code** (`src/` is bind-mounted read-only)
- **config.yaml** (mounted via volume)
- **Environment variables** in docker-compose.yml

```bash
# Restart specific services
podman-compose restart ingestion_service agent_core

# Or restart all
podman-compose restart
```

### 🔨 REBUILD required (slow, ~5-15 minutes)

Use `podman-compose build <service>` when changing:
- **Dockerfile** itself
- **pyproject.toml** (dependencies)
- **uv.lock** (locked dependencies)
- Base image updates

```bash
# Rebuild specific service (uses cache)
podman-compose build ingestion_service

# Rebuild without cache (nuclear option, very slow)
podman-compose build --no-cache ingestion_service
```

### 🚀 Speed Tips

1. **Never use `--no-cache` unless absolutely necessary**
2. **Dockerfile is optimized**: deps installed before source copy (better caching)
3. **Local base images**: Pull once, reuse forever
   ```bash
   podman pull python:3.11-slim-bookworm
   ```
4. **Check if rebuild is actually needed**:
   ```bash
   # See what changed
   git diff --name-only HEAD~1
   # If only .py files → restart is enough
   ```

## Model Configuration

Models are configured in `config.yaml`:
```yaml
llm:
  filter_model: "gpt-5-nano"    # Fast/cheap for filtering
  analysis_model: "gpt-5-mini"  # Quality for extraction/critic/curator
```

**Priority**: Environment vars > config.yaml > code defaults

To override temporarily:
```bash
LLM_FILTER_MODEL=gpt-4o-mini podman-compose restart ingestion_service
```

## Useful Commands

```bash
# View effective config on startup
podman logs ai-safety-radar_ingestion_service_1 | grep EFFECTIVE_CONFIG

# Monitor LLM calls
podman logs -f ai-safety-radar_ingestion_service_1 | grep LLM_

# Check Redis streams
podman exec ai-safety-radar_redis_1 redis-cli XLEN papers:pending
podman exec ai-safety-radar_redis_1 redis-cli XLEN papers:analyzed

# Safe reset (without breaking consumer groups)
podman exec ai-safety-radar_redis_1 redis-cli DEL papers:pending papers:analyzed
podman exec ai-safety-radar_redis_1 redis-cli XGROUP CREATE papers:pending agent_group 0 MKSTREAM
```
