# Security groups. Rules are separate resources so the cross-references
# (engine ← workers, task ← ALB) don't form inline cycles.

resource "aws_security_group" "alb" {
  name        = "${local.name}-alb"
  description = "Public ALB for automation-studio"
  vpc_id      = local.vpc_id
}

resource "aws_security_group" "web" {
  name        = "${local.name}-web"
  description = "automation-studio Fargate tasks"
  vpc_id      = local.vpc_id
}

resource "aws_security_group" "engine" {
  name        = "${local.name}-engine"
  description = "engine Fargate tasks"
  vpc_id      = local.vpc_id
}

resource "aws_security_group" "ec_worker" {
  name        = "${local.name}-ec-worker"
  description = "EC worker Fargate tasks"
  vpc_id      = local.vpc_id
}

# ── ALB: 80/443 in from the internet, all out ──
resource "aws_security_group_rule" "alb_in_https" {
  type              = "ingress"
  security_group_id = aws_security_group.alb.id
  from_port         = 443
  to_port           = 443
  protocol          = "tcp"
  cidr_blocks       = ["0.0.0.0/0"]
}

resource "aws_security_group_rule" "alb_in_http" {
  type              = "ingress"
  security_group_id = aws_security_group.alb.id
  from_port         = 80
  to_port           = 80
  protocol          = "tcp"
  cidr_blocks       = ["0.0.0.0/0"]
}

resource "aws_security_group_rule" "alb_out" {
  type              = "egress"
  security_group_id = aws_security_group.alb.id
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  cidr_blocks       = ["0.0.0.0/0"]
}

# ── web task: 8787 in from ALB, all out (Anthropic API, ECR via NAT) ──
resource "aws_security_group_rule" "web_in_alb" {
  type                     = "ingress"
  security_group_id        = aws_security_group.web.id
  from_port                = 8787
  to_port                  = 8787
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.alb.id
}

resource "aws_security_group_rule" "web_out" {
  type              = "egress"
  security_group_id = aws_security_group.web.id
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  cidr_blocks       = ["0.0.0.0/0"]
}

# ── engine task: 49134 in from web + ec-worker, all out ──
resource "aws_security_group_rule" "engine_in_web" {
  type                     = "ingress"
  security_group_id        = aws_security_group.engine.id
  from_port                = 49134
  to_port                  = 49134
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.web.id
}

resource "aws_security_group_rule" "engine_in_ec" {
  type                     = "ingress"
  security_group_id        = aws_security_group.engine.id
  from_port                = 49134
  to_port                  = 49134
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.ec_worker.id
}

resource "aws_security_group_rule" "engine_out" {
  type              = "egress"
  security_group_id = aws_security_group.engine.id
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  cidr_blocks       = ["0.0.0.0/0"]
}

# ── ec-worker task: no inbound, all out ──
resource "aws_security_group_rule" "ec_out" {
  type              = "egress"
  security_group_id = aws_security_group.ec_worker.id
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  cidr_blocks       = ["0.0.0.0/0"]
}
