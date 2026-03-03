#!/bin/bash
set -ex

yum update -y
yum install -y docker
systemctl start docker
systemctl enable docker

aws ecr get-login-password --region ${aws_region} | \
  docker login --username AWS --password-stdin ${aws_account_id}.dkr.ecr.${aws_region}.amazonaws.com

docker pull ${ecr_repo_url}:${image_tag}

docker run -d \
  --name jobscraper-frontend \
  --restart always \
  -p 80:80 \
  -e API_GATEWAY_URL=${api_gateway_url} \
  -e AWS_DEFAULT_REGION=${aws_region} \
  ${ecr_repo_url}:${image_tag}
