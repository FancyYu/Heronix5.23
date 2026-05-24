#!/bin/bash
# pull_dify_multi.sh - 多镜像源同时拉取 Dify 所需镜像
MIRRORS=(
    "docker.1ms.run"
    "docker.agsvpt.work"
)
IMAGES=(
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
current=0

for img in "${IMAGES[@]}"; do
    current=$((current+1))
    echo "[$current/$total] $img"
    
    # 检查是否已有
    if docker image inspect "$img" &>/dev/null; then
        echo "  └─ already exists"
        continue
    fi
    
    pulled=false
    for mirror in "${MIRRORS[@]}"; do
        echo "  └─ trying $mirror ..."
        if docker pull "$mirror/$img" &>/dev/null; then
            docker tag "$mirror/$img" "$img"
            echo "  └─ OK from $mirror"
            pulled=true
            break
        fi
    done
    
    if [ "$pulled" = false ]; then
        echo "  └─ FAILED from all mirrors"
    fi
done

echo ""
echo "--- Summary ---"
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}" | grep -v "^docker\.1ms\|^docker\.agsvpt\|^<none>"
echo ""
echo "Pull complete: $current images"