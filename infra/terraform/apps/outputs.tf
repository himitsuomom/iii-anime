output "deploy_role_arn" {
  description = "Set this as the GitHub Actions secret AWS_DEPLOY_ROLE_ARN (deploy-apps.yml)."
  value       = aws_iam_role.github_deploy_apps.arn
}

output "ecr_registry" {
  description = "Set this as the GitHub Actions variable ECR_REGISTRY (deploy-apps.yml)."
  value       = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${var.aws_region}.amazonaws.com"
}

output "repository_urls" {
  description = "Full ECR repository URLs, keyed by repo name."
  value       = { for name, r in aws_ecr_repository.app : name => r.repository_url }
}
