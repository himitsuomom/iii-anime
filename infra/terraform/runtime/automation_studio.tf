resource "aws_ecs_task_definition" "automation_studio" {
  family                   = "iii-automation-studio"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.web_cpu
  memory                   = var.web_memory
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn

  container_definitions = jsonencode([
    {
      name      = "automation-studio"
      image     = var.automation_studio_image
      essential = true
      portMappings = [
        { containerPort = 8787, protocol = "tcp" },
      ]
      environment = [
        { name = "PORT", value = "8787" },
        { name = "III_URL", value = local.engine_url },
        { name = "III_TELEMETRY_ENABLED", value = "false" },
      ]
      secrets = [
        { name = "ANTHROPIC_API_KEY", valueFrom = var.anthropic_secret_arn },
        { name = "SHOPIFY_WEBHOOK_SECRET", valueFrom = var.shopify_webhook_secret_arn },
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.automation_studio.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "automation-studio"
        }
      }
    }
  ])
}

resource "aws_ecs_service" "automation_studio" {
  name            = "iii-automation-studio"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.automation_studio.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = local.private_subnet_ids
    security_groups  = [aws_security_group.web.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.web.arn
    container_name   = "automation-studio"
    container_port   = 8787
  }

  # The ALB target group must be attached to a listener before the service
  # registers targets.
  depends_on = [aws_lb_listener.https, aws_ecs_service.engine]
}
