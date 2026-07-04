# The EC2 box runs the reverse proxy (80/443), the API server, Postgres and Redis.
resource "aws_security_group" "ec2" {
  name        = "${var.project_name}-ec2-sg"
  description = "DeployX EC2 host: reverse proxy + api + postgres + redis"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "SSH - key pair auth is the real gate here, no IP lock"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTP for the reverse proxy / wildcard subdomains"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTPS (add once you wire up certs)"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-ec2-sg"
  }
}

# The ECS Fargate build-worker tasks. They only need outbound access
# (git clone, npm install, talk back to Postgres/Redis/S3) — nothing
# needs to reach them, so no ingress rules.
resource "aws_security_group" "ecs_tasks" {
  name        = "${var.project_name}-ecs-tasks-sg"
  description = "DeployX ECS Fargate build-worker tasks"
  vpc_id      = data.aws_vpc.default.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-ecs-tasks-sg"
  }
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
