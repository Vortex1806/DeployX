resource "aws_ecs_cluster" "this" {
  name = "${var.project_name}-cluster"
}

resource "aws_cloudwatch_log_group" "build_worker" {
  name              = "/ecs/${var.project_name}-build-worker"
  retention_in_days = 7
}

# Lets ECS pull the image from ECR and write logs to CloudWatch.
resource "aws_iam_role" "task_execution" {
  name = "${var.project_name}-ecs-task-execution"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "task_execution" {
  role       = aws_iam_role.task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# What the build-worker container itself is allowed to do: only
# write objects into its own output bucket. Nothing else.
resource "aws_iam_role" "task" {
  name = "${var.project_name}-ecs-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "task_s3_write" {
  name = "${var.project_name}-task-s3-write"
  role = aws_iam_role.task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["s3:PutObject"]
      Resource = "${aws_s3_bucket.output.arn}/*"
    }]
  })
}

resource "aws_ecs_task_definition" "build_worker" {
  family                   = "${var.project_name}-build-worker"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "512"
  memory                   = "1024"
  execution_role_arn       = aws_iam_role.task_execution.arn
  task_role_arn            = aws_iam_role.task.arn

  # NOTE: POSTGRES_PASSWORD below is a plaintext container env var, visible to
  # anyone with ecs:DescribeTaskDefinition on this account. Fine for a 2-day
  # build behind your own AWS account; before this is "enterprise grade" for
  # real, move it into Secrets Manager and reference it via task definition
  # `secrets` instead of `environment`.
  container_definitions = jsonencode([
    {
      name      = "build-worker"
      image     = "${aws_ecr_repository.build_worker.repository_url}:latest"
      essential = true
      environment = [
        { name = "S3_BUCKET", value = aws_s3_bucket.output.bucket },
        { name = "AWS_REGION", value = var.aws_region },
        { name = "REDIS_HOST", value = aws_instance.host.private_ip },
        { name = "REDIS_PORT", value = "6379" },
        { name = "POSTGRES_HOST", value = aws_instance.host.private_ip },
        { name = "POSTGRES_PORT", value = "5432" },
        { name = "POSTGRES_DB", value = "deployx" },
        { name = "POSTGRES_USER", value = "deployx" },
        { name = "POSTGRES_PASSWORD", value = var.postgres_password }
        # GIT_REPOSITORY_URL, PROJECT_ID, DEPLOYMENT_ID are injected per-run
        # by the api-server via the RunTask containerOverrides, not fixed here.
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.build_worker.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "build"
        }
      }
    }
  ])
}
