resource "aws_ecs_task_definition" "ec_worker" {
  family                   = "iii-ec-worker"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.worker_cpu
  memory                   = var.worker_memory
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn

  container_definitions = jsonencode([
    {
      name      = "ec-worker"
      image     = var.ec_worker_image
      essential = true
      environment = [
        { name = "III_URL", value = local.engine_url },
        { name = "III_TELEMETRY_ENABLED", value = "false" },
        { name = "EC_DESCRIBE_BACKEND", value = "remote" },
      ]
      secrets = [
        { name = "ANTHROPIC_API_KEY", valueFrom = var.anthropic_secret_arn },
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.ec_worker.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ec-worker"
        }
      }
    }
  ])
}

resource "aws_ecs_service" "ec_worker" {
  name            = "iii-ec-worker"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.ec_worker.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = local.private_subnet_ids
    security_groups  = [aws_security_group.ec_worker.id]
    assign_public_ip = false
  }

  # Start the worker after the engine is registered in Cloud Map.
  depends_on = [aws_ecs_service.engine]
}
