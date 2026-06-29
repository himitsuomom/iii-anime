resource "aws_ecs_cluster" "main" {
  name = local.name

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

# Private DNS namespace so workers can resolve the engine by name.
resource "aws_service_discovery_private_dns_namespace" "internal" {
  name        = "iii.local"
  description = "Service discovery for the iii runtime stack"
  vpc         = local.vpc_id
}

# Registers engine tasks as engine.iii.local (A records, one per task IP).
resource "aws_service_discovery_service" "engine" {
  name = "engine"

  dns_config {
    namespace_id   = aws_service_discovery_private_dns_namespace.internal.id
    routing_policy = "MULTIVALUE"

    dns_records {
      ttl  = 10
      type = "A"
    }
  }

  health_check_custom_config {
    failure_threshold = 1
  }
}
