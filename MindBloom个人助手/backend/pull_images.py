"""通过工作镜像拉取 Dify 所需的所有 Docker 镜像。"""
import subprocess
import sys

MIRROR = "docker.1ms.run"

IMAGES = [
    "busybox:latest",
    "langgenius/dify-api:1.14.2",
    "langgenius/dify-web:1.14.2",
    "postgres:15-alpine",
    "redis:6-alpine",
    "langgenius/dify-sandbox:0.2.15",
    "langgenius/dify-plugin-daemon:0.6.1-local",
    "ubuntu/squid:latest",
    "nginx:latest",
]


def run(cmd):
    print(f"  → {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"    失败: {result.stderr.strip()[:100]}")
        return False
    for line in result.stdout.strip().split("\n")[-3:]:
        if line.strip():
            print(f"    {line.strip()}")
    return True


def main():
    for image in IMAGES:
        mirror_image = f"{MIRROR}/{image}"
        print(f"\n{'=' * 50}")
        print(f"镜像: {image}")

        if run(["docker", "pull", mirror_image]):
            run(["docker", "tag", mirror_image, image])
        else:
            print(f"  ⚠ 跳过 {image}，继续下一个")
    print(f"\n{'=' * 50}")
    print("拉取完成！")


if __name__ == "__main__":
    main()