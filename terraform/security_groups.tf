# The EC2 box runs the reverse proxy (80/443), the API server, Postgres and Redis.
#
# NOTE: every rule for both security groups below is a standalone
# aws_security_group_rule resource — none of the aws_security_group blocks
# use inline ingress/egress. Mixing the two for the same group is a known
# Terraform footgun: the inline block is treated as the complete, authoritative
# rule set, so any unrelated `apply` silently reverts the group back to just
# the inline rules, deleting anything added via a separate rule resource.
# That's exactly what deleted the Postgres/Redis rules here once before —
# keeping everything as standalone rules avoids it for good.
resource "aws_security_group" "ec2" {
  name        = "${var.project_name}-ec2-sg"
  description = "DeployX EC2 host: reverse proxy + api + postgres + redis"
  vpc_id      = data.aws_vpc.default.id

  tags = {
    Name = "${var.project_name}-ec2-sg"
  }
}

resource "aws_security_group_rule" "ec2_ssh" {
  type              = "ingress"
  from_port         = 22
  to_port           = 22
  protocol          = "tcp"
  security_group_id = aws_security_group.ec2.id
  cidr_blocks       = ["0.0.0.0/0"]
  description       = "SSH - key pair auth is the real gate here, no IP lock"
}

resource "aws_security_group_rule" "ec2_http" {
  type              = "ingress"
  from_port         = 80
  to_port           = 80
  protocol          = "tcp"
  security_group_id = aws_security_group.ec2.id
  cidr_blocks       = ["0.0.0.0/0"]
  description       = "HTTP for the reverse proxy / wildcard subdomains"
}

resource "aws_security_group_rule" "ec2_https" {
  type              = "ingress"
  from_port         = 443
  to_port           = 443
  protocol          = "tcp"
  security_group_id = aws_security_group.ec2.id
  cidr_blocks       = ["0.0.0.0/0"]
  description       = "HTTPS (add once you wire up certs)"
}

resource "aws_security_group_rule" "ec2_egress_all" {
  type              = "egress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  security_group_id = aws_security_group.ec2.id
  cidr_blocks       = ["0.0.0.0/0"]
}

# The ECS Fargate build-worker tasks. They only need outbound access
# (git clone, npm install, talk back to Postgres/Redis/S3) — nothing
# needs to reach them, so no ingress rules of their own.
resource "aws_security_group" "ecs_tasks" {
  name        = "${var.project_name}-ecs-tasks-sg"
  description = "DeployX ECS Fargate build-worker tasks"
  vpc_id      = data.aws_vpc.default.id

  tags = {
    Name = "${var.project_name}-ecs-tasks-sg"
  }
}

resource "aws_security_group_rule" "ecs_tasks_egress_all" {
  type              = "egress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  security_group_id = aws_security_group.ecs_tasks.id
  cidr_blocks       = ["0.0.0.0/0"]
}

# Let build-worker tasks reach Postgres and Redis on the EC2 box,
# without opening those ports to the whole internet.
resource "aws_security_group_rule" "ec2_allow_postgres_from_ecs" {
  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  security_group_id        = aws_security_group.ec2.id
  source_security_group_id = aws_security_group.ecs_tasks.id
  description              = "Postgres from ECS build tasks"
}

resource "aws_security_group_rule" "ec2_allow_redis_from_ecs" {
  type                     = "ingress"
  from_port                = 6379
  to_port                  = 6379
  protocol                 = "tcp"
  security_group_id        = aws_security_group.ec2.id
  source_security_group_id = aws_security_group.ecs_tasks.id
  description              = "Redis from ECS build tasks"
}
