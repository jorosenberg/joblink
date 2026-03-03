resource "aws_secretsmanager_secret" "db_credentials" {
  name                    = "${local.project_name}/db-credentials"
  recovery_window_in_days = 0
  tags                    = local.common_tags
}

resource "aws_secretsmanager_secret_version" "db_credentials" {
  secret_id = aws_secretsmanager_secret.db_credentials.id
  secret_string = jsonencode({
    username = var.db_username
    password = var.db_password
    host     = aws_db_instance.jobsdb.address
    port     = 5432
    dbname   = "jobscraper"
  })
}

resource "aws_secretsmanager_secret" "scrape_password" {
  name                    = "${local.project_name}/scrape-password"
  recovery_window_in_days = 0
  tags                    = local.common_tags
}

resource "aws_secretsmanager_secret_version" "scrape_password" {
  secret_id     = aws_secretsmanager_secret.scrape_password.id
  secret_string = var.scrape_password
}

resource "aws_secretsmanager_secret" "hf_token" {
  name                    = "${local.project_name}/hf-token"
  recovery_window_in_days = 0
  tags                    = local.common_tags
}

resource "aws_secretsmanager_secret_version" "hf_token" {
  secret_id     = aws_secretsmanager_secret.hf_token.id
  secret_string = var.hf_token
}
