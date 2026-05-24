#!/bin/bash
MIRROR="docker.1ms.run"
IMAGES=(
    "busybox:latest"
    "langgenius/dify-api:1.14.2"
    "langgenius/dify-web:1.14.2"
    "postgres:15-alpine"
    "redis:6-alpine"
    "langgenius/dify-sandbox:0.2.15"
    "langgenius/dify-plugin-daemon:0.6.1-local"
    "ubuntu/squid:latest"
    "nginx:latest"
    "semitechnologies/weaviate:1.27.0"
)
total=${#IMAGES[@]}
i=1
for img in "${IMAGES[@]}"; do
    echo "[$i/$total] Pulling $img ..."
    if docker pull "$MIRROR/$img"; then
        docker tag "$MIRROR/$img" "$img"
        echo "  OK: $img"
    else
        echo "  SKIP: $img (failed)"
    fi
    i=$((i+1))
done
echo "All done!"