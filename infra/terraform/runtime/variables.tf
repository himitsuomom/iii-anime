variable "aws_region" {
  description = "AWS region for the runtime stack."
  type        = string
  default     = "us-east-1"
}

variable "domain" {
  description = "Public hostname for automation-studio (must be under the iii.dev Route53 zone), e.g. app.iii.dev."
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR block for the runtime VPC."
  type        = string
  default     = "10.42.0.0/16"
}

# ── Container images (ECR URI:tag, e.g. <acct>.dkr.ecr.us-east-1.amazonaws.com/iii-engine:abc123) ──
variable "engine_image" {
  description = "Engine image (config-baked, from deploy/engine.Dockerfile)."
  type        = string
}

variable "ec_worker_image" {
  description = "EC worker image (apps/ec)."
  type        = string
}

variable "automation_studio_image" {
  description = "automation-studio image (apps/automation-studio)."
  type        = string
}

# ── Secrets (pre-created in Secrets Manager; values never live in Terraform) ──
variable "anthropic_secret_arn" {
  description = "Secrets Manager ARN holding the ANTHROPIC_API_KEY value."
  type        = string
}

variable "shopify_webhook_secret_arn" {
  description = "Secrets Manager ARN holding the SHOPIFY_WEBHOOK_SECRET value."
  type        = string
}

# ── Per-service sizing ──
variable "engine_cpu" {
  type    = number
  default = 512
}
variable "engine_memory" {
  type    = number
  default = 1024
}
variable "worker_cpu" {
  type    = number
  default = 256
}
variable "worker_memory" {
  type    = number
  default = 512
}
variable "web_cpu" {
  type    = number
  default = 256
}
variable "web_memory" {
  type    = number
  default = 512
}
variable "desired_count" {
  description = "Desired task count for each service."
  type        = number
  default     = 1
}
