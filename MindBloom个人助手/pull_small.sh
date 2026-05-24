#!/bin/bash
# 快速拉取小镜像
MIRROR="docker.1ms.run"
IMAGES=(
    "postgres:15-alpine"
    "nginx:latest"
    "ubuntu/squid:latest"
    "langgenius/dify-sandbox:0.2.15"
    "langgenius/dify-plugin-daemon:0.6.1-local"
    "semitechnologies/weaviate:1.27.0"
)
for img in "${IMAGES[@]}"; do
    if ! docker image inspect "$img" &>/dev/null; then
        echo "Pulling $img ..."
        docker pull "$MIRROR/$img" && docker tag "$MIRROR/$img" "$img" && echo "  OK"
    else
        echo "Exists: $img"
    fi
done
echo "Small images done!"
echo ""
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}" | grep -v "^docker\.1ms"