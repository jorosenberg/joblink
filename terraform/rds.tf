resource "aws_db_subnet_group" "main" {
  name       = "${local.project_name}-db-subnet"
  subnet_ids = [aws_subnet.private_a.id, aws_subnet.private_b.id]
  tags       = local.common_tags
}

resource "aws_db_instance" "jobsdb" {
  identifier              = "${local.project_name}-db"
  engine                  = "postgres"
  engine_version          = "15"
  instance_class          = "db.t3.micro"
  allocated_storage       = 20
  storage_type            = "gp2"
  db_name                 = "jobsdb"
  username                = var.db_username
  password                = var.db_password
  db_subnet_group_name    = aws_db_subnet_group.main.name
  vpc_security_group_ids  = [aws_security_group.rds.id]
  publicly_accessible     = true
  skip_final_snapshot     = true
  backup_retention_period = 0
  multi_az                = false
  tags                    = local.common_tags
}
