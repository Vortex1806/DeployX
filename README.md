# DeployX

A from-scratch, Python/FastAPI rewrite of the Vercel-clone build ("Vortex Deploy"),
running on free-tier AWS: one EC2 box for the always-on services, ECS Fargate
for ephemeral build tasks, S3 static website hosting for output — no EKS,
no RDS/ElastiCache, no CloudFront/Route53.

## Repo layout

```
deployx/
  terraform/              infra: ECS cluster, ECR, S3, EC2, security groups, IAM
  ec2/
    docker-compose.yml     runs on the EC2 host: postgres, redis (+ api-server, reverse-proxy later)
    user_data.sh            cloud-init: installs docker on first boot
  docker-compose.dev.yml   local-only postgres+redis for building the api-server on your laptop
  api-server/              (next) FastAPI app
  build-worker/            (next) the container ECS runs per deployment
  reverse-proxy/           (next) subdomain -> S3 website router
```

## Day 1, hour 0-1: stand up the infra

1. `cd terraform`
2. `cp terraform.tfvars.example terraform.tfvars` and fill in:
   - `key_pair_name` — an EC2 key pair that already exists in `ap-south-1` (create one in the console under EC2 > Key Pairs if you don't have one — you'll need the downloaded `.pem` to SSH in)

   SSH (port 22) is open to `0.0.0.0/0` since your IP moves around — key-pair auth is
   the actual gate. Worth adding `fail2ban` on the box at some point (`sudo apt install
   fail2ban`) to cut down on brute-force noise in the logs, but not urgent for a 2-day build.
3. `terraform init`
4. `terraform plan` — read through it, this is the whole footprint of the project
5. `terraform apply`
6. Note the outputs: `ec2_public_ip`, `s3_website_endpoint`, `ecr_repository_url`, `ecs_cluster_name`, `ecs_task_definition_arn`, `ecs_subnet_id`, `ecs_tasks_security_group_id` — the api-server's `.env` will need most of these.

## Day 1, hour 1-2: get docker-compose running on the box

```
scp -i /path/to/your-key.pem ec2/docker-compose.yml ubuntu@<ec2_public_ip>:/opt/deployx/
ssh -i /path/to/your-key.pem ubuntu@<ec2_public_ip>
cd /opt/deployx
echo "POSTGRES_PASSWORD=<pick-something>" > .env
sudo docker compose up -d
sudo docker compose ps    # confirm postgres + redis are up
```

Cloud-init takes 30-60s to finish installing docker after the instance first boots —
if `docker` isn't found yet, wait a bit and retry.

## What's next

- `api-server/` — FastAPI + SQLModel + Alembic, `POST /project`, `POST /deploy` triggering
  `ecs:RunTask` via boto3 (Day 1, hour 2-4)
- `build-worker/` — Dockerfile + Python build script (Day 1, hour 4-6)
- End-to-end test against a real static repo (Day 1, hour 6-8)

## Cost / cleanup

Everything here fits free tier (EC2 t3.micro, ECS Fargate billed per-second only while
a build runs, S3, ECR). Still — if you're stopping for the day and want to be safe,
`terraform destroy` and re-`apply` tomorrow; the whole stack takes under 2 minutes to
come back up.
