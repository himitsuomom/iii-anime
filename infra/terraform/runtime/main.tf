terraform {
  backend "s3" {
    bucket         = "iii-terraform-state-prod-us-east-1"
    key            = "runtime/terraform.tfstate"
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
      Service     = "runtime"
      Module      = "infra/terraform/runtime"
      ManagedBy   = "terraform"
    }
  }
}

data "aws_caller_identity" "current" {}

data "aws_route53_zone" "iii_dev" {
  name         = "iii.dev."
  private_zone = false
}

locals {
  name = "iii-apps-prod"
  azs  = ["${var.aws_region}a", "${var.aws_region}b"]
  # Internal engine address that the workers connect to (Cloud Map).
  engine_url = "ws://engine.${aws_service_discovery_private_dns_namespace.internal.name}:49134"
}
