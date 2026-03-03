variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "db_username" {
  type      = string
  sensitive = true
}

variable "db_password" {
  type      = string
  sensitive = true
}

variable "scrape_password" {
  type        = string
  sensitive   = true
  description = "Password required to use scraping and delete functionality"
}

variable "hf_token" {
  type        = string
  sensitive   = true
  description = "Hugging Face API token for model downloads"
}

variable "ec2_key_pair_name" {
  type    = string
  default = ""
}

variable "frontend_image_tag" {
  type    = string
  default = "latest"
}

variable "api_image_tag" {
  type    = string
  default = "latest"
}

variable "scraper_image_tag" {
  type    = string
  default = "latest"
}

variable "analysis_image_tag" {
  type    = string
  default = "latest"
}
