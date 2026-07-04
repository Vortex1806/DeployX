variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "ap-south-1"
}

variable "project_name" {
  description = "Prefix used for naming every resource"
  type        = string
  default     = "deployx"
}

variable "key_pair_name" {
  description = "Name of an existing EC2 key pair in this region (create one in the AWS console first)"
  type        = string
}

variable "instance_type" {
  description = "EC2 instance type for the docker-compose host"
  type        = string
  default     = "t3.micro"
}
