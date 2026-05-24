import subprocess
import sys

MIRROR = "docker.1ms.run"
IMAGES = [
    ("busybox:latest", 0),
    ("langgenius/dify-api:1.14.2", 1),
    ("langgenius/dify-web:1.14.2", 2),
    ("postgres:15-alpine", 3),
    ("redis:6-alpine", 4),
    ("langgenius/dify-sandbox:0.2.15", 5),
    ("langgenius/dify-plugin-daemon:0.6.1-local", 6),
    ("ubuntu/squid:latest", 7),
    ("nginx:latest", 8),
    ("semitechnologies/weaviate:1.27.0", 9),
]

total = len(IMAGES)

for idx, (image, _) in enumerate(IMAGES, 1):
    mirror_image = f"{MIRROR}/{image}"
    print(f"[{idx}/{total}] Pulling {image} ...")
    sys.stdout.flush()
    r = subprocess.run(
        ["docker", "pull", mirror_image],
        capture_output=True, text=True, timeout=600
    )
    if r.returncode == 0:
        subprocess.run(
            ["docker", "tag", mirror_image, image],
            capture_output=True, text=True, timeout=30
        )
        print(f"  OK: {image}")
    else:
        err = r.stderr.strip()[:200]
        print(f"  FAIL: {err}")
    sys.stdout.flush()

print("All done!")