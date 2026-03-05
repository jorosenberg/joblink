resource "aws_lambda_function" "api" {
  function_name = "${local.project_name}-api"
  role          = aws_iam_role.lambda_api.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.api.repository_url}:${var.api_image_tag}"
  timeout       = 30
  memory_size   = 512

  environment {
    variables = {
      DB_SECRET_ARN       = aws_secretsmanager_secret.db_credentials.arn
      DB_HOST             = aws_db_instance.jobsdb.address
      DB_NAME             = "jobsdb"
      SCRAPE_PASSWORD_ARN = aws_secretsmanager_secret.scrape_password.arn
    }
  }

  tags = local.common_tags
}

resource "aws_lambda_function" "scraper" {
  function_name = "${local.project_name}-scraper"
  role          = aws_iam_role.lambda_scraper.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.scraper.repository_url}:${var.scraper_image_tag}"
  timeout       = 900
  memory_size   = 512

  environment {
    variables = {
      DB_SECRET_ARN        = aws_secretsmanager_secret.db_credentials.arn
      DB_HOST              = aws_db_instance.jobsdb.address
      DB_NAME              = "jobsdb"
      ANALYSIS_LAMBDA_NAME = "${local.project_name}-analysis"
      SCRAPE_PASSWORD_ARN  = aws_secretsmanager_secret.scrape_password.arn
      EC2_SCRAPE_URL       = "http://${aws_instance.frontend.public_ip}/internal/selenium-scrape"
    }
  }

  tags = local.common_tags

  depends_on = [aws_lambda_function.analysis]
}

resource "aws_lambda_function" "analysis" {
  function_name = "${local.project_name}-analysis"
  role          = aws_iam_role.lambda_analysis.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.analysis.repository_url}:${var.analysis_image_tag}"
  timeout       = 900
  memory_size   = 3008

  environment {
    variables = {
      DB_SECRET_ARN = aws_secretsmanager_secret.db_credentials.arn
      DB_HOST       = aws_db_instance.jobsdb.address
      DB_NAME       = "jobsdb"
      HF_TOKEN_ARN  = aws_secretsmanager_secret.hf_token.arn
    }
  }

  tags = local.common_tags
}
