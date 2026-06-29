resource "aws_ecs_task_definition" "engine" {
  family                   = "iii-engine"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.engine_cpu
  memory                   = var.engine_memory
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn

  container_definitions = jsonencode([
    {
      name      = "engine"
      image     = var.engine_image
      essential = true
      portMappings = [
        { containerPort = 49134, protocol = "tcp" },
        { containerPort = 3111, protocol = "tcp" },
      ]
      environment = [
        { name = "III_EXECUTION_CONTEXT", value = "docker" },
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.engine.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "engine"
        }
      }
    }
  ])
}

resource "aws_ecs_service" "engine" {
  name            = "iii-engine"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.engine.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = local.private_subnet_ids
    security_groups  = [aws_security_group.engine.id]
    assign_public_ip = false
  }

  service_registries {
    registry_arn = aws_service_discovery_service.engine.arn
  }
}
