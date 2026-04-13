terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  backend "s3" {
    bucket         = "jobscraper-tf-state"
    key            = "terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "jobscraper-terraform-lock"
    encrypt        = true
  }
}

provider "aws" {
  region = var.aws_region
}

locals {
  project_name = "jobscraper"
  environment  = "prod"
  common_tags = {
    Project     = local.project_name
    Environment = local.environment
    ManagedBy   = "terraform"
  }
}

data "aws_caller_identity" "current" {}
