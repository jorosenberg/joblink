data "aws_ami" "amazon_linux_2023" {
  most_recent = true
  owners      = ["amazon"]
  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }
}

resource "aws_instance" "frontend" {
  ami                    = data.aws_ami.amazon_linux_2023.id
  instance_type          = "t2.micro"
  subnet_id              = aws_subnet.public_a.id
  vpc_security_group_ids = [aws_security_group.ec2_frontend.id]
  iam_instance_profile   = aws_iam_instance_profile.ec2_frontend.name
  key_name               = var.ec2_key_pair_name

  user_data = base64encode(templatefile("${path.module}/scripts/userdata.sh.tpl", {
    aws_region      = var.aws_region
    ecr_repo_url    = aws_ecr_repository.frontend.repository_url
    image_tag       = var.frontend_image_tag
    api_gateway_url = aws_apigatewayv2_api.main.api_endpoint
    aws_account_id  = data.aws_caller_identity.current.account_id
  }))

  tags = merge(local.common_tags, { Name = "${local.project_name}-frontend" })
}
