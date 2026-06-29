variable "aws_region" {
  description = "AWS region for the ECR repositories and IAM role."
  type        = string
  default     = "us-east-1"
}

variable "github_repo" {
  description = "owner/name of the GitHub repository allowed to assume the deploy role."
  type        = string
  default     = "iii-hq/iii"
}

variable "github_environment" {
  description = "GitHub Actions environment that may assume the deploy role (matches deploy-apps.yml)."
  type        = string
  default     = "iii-apps-prod"
}

variable "app_repos" {
  description = "ECR repository names, one per deployable image (engine + workers)."
  type        = list(string)
  default     = ["iii-engine", "iii-ec-worker", "iii-automation-studio", "iii-arbitrage-worker"]
}

variable "image_retention_count" {
  description = "Number of most-recent images to keep per ECR repo (older untagged images are expired)."
  type        = number
  default     = 10
}
