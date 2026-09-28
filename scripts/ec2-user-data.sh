#!/bin/bash
# EC2 user data for Amazon Linux 2023 (optional alternative to the manual
# SSH steps). Paste it into "Advanced details > User data" when launching the
# instance, after replacing <dockerhub-user>. It installs Docker and starts
# the container on host port 8080. Output: /var/log/cloud-init-output.log
set -euxo pipefail

IMAGE="<dockerhub-user>/virtualization-lab:1.0"

dnf update -y
dnf install -y docker
systemctl enable --now docker
usermod -a -G docker ec2-user

docker pull "$IMAGE"
docker run -d \
  --name virtualization-lab \
  --restart unless-stopped \
  -e PORT=9000 \
  -p 8080:9000 \
  "$IMAGE"
