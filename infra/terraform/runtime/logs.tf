resource "aws_cloudwatch_log_group" "engine" {
  name              = "/ecs/iii-engine"
  retention_in_days = 14
}

resource "aws_cloudwatch_log_group" "ec_worker" {
  name              = "/ecs/iii-ec-worker"
  retention_in_days = 14
}

resource "aws_cloudwatch_log_group" "automation_studio" {
  name              = "/ecs/iii-automation-studio"
  retention_in_days = 14
}
