output "ec2_public_ip" {
  value = aws_eip.host.public_ip
}

output "s3_bucket_name" {
  value = aws_s3_bucket.output.bucket
}

output "s3_website_endpoint" {
  value = aws_s3_bucket_website_configuration.output.website_endpoint
}

output "ecr_repository_url" {
  value = aws_ecr_repository.build_worker.repository_url
}

output "ecs_cluster_name" {
  value = aws_ecs_cluster.this.name
}

output "ecs_task_definition_arn" {
  value = aws_ecs_task_definition.build_worker.arn
}

output "ecs_subnet_id" {
  value = data.aws_subnets.default.ids[0]
}

output "ecs_tasks_security_group_id" {
  value = aws_security_group.ecs_tasks.id
}

output "postgres_password" {
  value     = var.postgres_password
  sensitive = true
}
