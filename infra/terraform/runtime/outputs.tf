output "app_url" {
  description = "Public URL of automation-studio."
  value       = "https://${var.domain}"
}

output "alb_dns_name" {
  description = "ALB DNS name (the Route53 record aliases to this)."
  value       = aws_lb.app.dns_name
}

output "cluster_name" {
  description = "ECS cluster name — set as the GitHub Actions variable ECS_CLUSTER (deploy-apps.yml)."
  value       = aws_ecs_cluster.main.name
}

output "service_names" {
  description = "ECS service names, matching the deploy-apps.yml matrix `service` values."
  value = {
    engine            = aws_ecs_service.engine.name
    ec_worker         = aws_ecs_service.ec_worker.name
    automation_studio = aws_ecs_service.automation_studio.name
  }
}
