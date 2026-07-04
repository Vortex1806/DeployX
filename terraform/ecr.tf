resource "aws_ecr_repository" "build_worker" {
  name                 = "${var.project_name}-build-worker"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

# Keep only the last 10 images so ECR storage doesn't creep past the free tier.
resource "aws_ecr_lifecycle_policy" "build_worker" {
  repository = aws_ecr_repository.build_worker.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 10 images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 10
        }
        action = { type = "expire" }
      }
    ]
  })
}
