output "api_gateway_url" {
  value = aws_apigatewayv2_api.main.api_endpoint
}

output "frontend_public_ip" {
  value = aws_instance.frontend.public_ip
}

output "rds_endpoint" {
  value     = aws_db_instance.jobsdb.address
  sensitive = true
}

output "ecr_api_repo" {
  value = aws_ecr_repository.api.repository_url
}

output "ecr_scraper_repo" {
  value = aws_ecr_repository.scraper.repository_url
}

output "ecr_analysis_repo" {
  value = aws_ecr_repository.analysis.repository_url
}

output "ecr_frontend_repo" {
  value = aws_ecr_repository.frontend.repository_url
}
