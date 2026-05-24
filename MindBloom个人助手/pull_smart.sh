#!/bin/bash
# 分两轮拉取：先小镜像，再大镜像

MIRROR="docker.1ms.run"

SMALL_IMAGES=(
    "postgres:15-alpine"
    "nginx:latest"
    "ubuntu/squid:latest"
    "langgenius/dify-sandbox:0.2.15"
    "langgenius/dify-plugin-daemon:0.6.1-local"
    "semitechnologies/weaviate:1.27.0"
)

BIG_IMAGES=(
    "langgenius/dify-api:1.14.2"
    "langgenius/dify-web:1.14.2"
)

pull_one() {
    local img="$1"
    local mirror="$2"
    if docker image inspect "$img" &>/dev/null; then
        echo "  └─ exists"
        return 0
    fi
    echo "  └─ pulling $mirror/$img ..."
    if docker pull "$mirror/$img" 2>/dev/null; then
        docker tag "$mirror/$img" "$img"
        echo "  └─ OK"
        return 0
    fi
    return 1
}

echo "=== Round 1: Small images ==="
total=${#SMALL_IMAGES[@]}
i=0
for img in "${SMALL_IMAGES[@]}"; do
    i=$((i+1))
    echo "[$i/$total] $img"
    pull_one "$img" "$MIRROR" || echo "  └─ SKIP"
done

echo ""
echo "=== Round 2: Big images (may be slow) ==="
for img in "${BIG_IMAGES[@]}"; do
    echo "    $img"
    pull_one "$img" "$MIRROR" || echo "  └─ SKIP"
done

echo ""
echo "=== Final: Images ready ==="
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}" | grep -v "^docker\.1ms\|^<none>"