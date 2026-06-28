terraform {
  backend "s3" {
    bucket         = "iii-terraform-state-prod-us-east-1"
    key            = "apps/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "iii-terraform-locks-prod"
    encrypt        = true
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "iii"
      Environment = "prod"
      Service     = "apps"
      Module      = "infra/terraform/apps"
      ManagedBy   = "terraform"
    }
  }
}

data "aws_caller_identity" "current" {}

# The GitHub OIDC provider is a per-account singleton created by the website
# module (infra/terraform/website/iam_github_oidc.tf). Reference it here rather
# than creating a duplicate.
data "aws_iam_openid_connect_provider" "github" {
  url = "https://token.actions.githubusercontent.com"
}
