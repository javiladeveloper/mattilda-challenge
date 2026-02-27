# AWS Infrastructure - Mattilda Backend

This folder contains AWS infrastructure configuration for deploying the Mattilda Backend.

## Architecture Overview

```
                                    ┌─────────────────────────────────────────────┐
                                    │                    AWS Cloud                 │
                                    │                                              │
    ┌──────────┐                    │  ┌─────────────────────────────────────┐    │
    │  Users   │────────────────────┼──│         Application Load Balancer   │    │
    └──────────┘                    │  │              (HTTPS:443)             │    │
                                    │  └─────────────────┬───────────────────┘    │
                                    │                    │                         │
                                    │  ┌─────────────────┴───────────────────┐    │
                                    │  │           ECS Fargate Cluster        │    │
                                    │  │  ┌─────────────┐  ┌─────────────┐   │    │
                                    │  │  │  Task 1     │  │  Task 2     │   │    │
                                    │  │  │  (API)      │  │  (API)      │   │    │
                                    │  │  └──────┬──────┘  └──────┬──────┘   │    │
                                    │  └─────────┼────────────────┼──────────┘    │
                                    │            │                │                │
                                    │  ┌─────────┴────────────────┴──────────┐    │
                                    │  │           Private Subnets            │    │
                                    │  │  ┌─────────────┐  ┌─────────────┐   │    │
                                    │  │  │   RDS       │  │  ElastiCache│   │    │
                                    │  │  │ PostgreSQL  │  │    Redis    │   │    │
                                    │  │  └─────────────┘  └─────────────┘   │    │
                                    │  └─────────────────────────────────────┘    │
                                    │                                              │
                                    └─────────────────────────────────────────────┘
```

## Components

### Compute
- **ECS Fargate**: Serverless container orchestration
- **Auto Scaling**: 2-10 tasks based on CPU/Memory

### Database
- **RDS PostgreSQL 15**: Managed relational database
- **Multi-AZ**: Production only for high availability

### Caching
- **ElastiCache Redis**: In-memory caching layer

### Networking
- **VPC**: Isolated network with public/private subnets
- **ALB**: Application Load Balancer with HTTPS termination
- **Security Groups**: Firewall rules for each component

### CI/CD
- **GitHub Actions**: Automated build, test, and deploy
- **ECR**: Container image registry

## Deployment Workflow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Commit    │────▶│    Build    │────▶│    Test     │────▶│   Deploy    │
│   to Git    │     │   Docker    │     │   Pytest    │     │   to ECS    │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
       │                                                            │
       │                                                            ▼
       │            ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
       │            │   Rollback  │◀────│   Monitor   │◀────│   Health    │
       └───────────▶│  (if needed)│     │  CloudWatch │     │   Check     │
                    └─────────────┘     └─────────────┘     └─────────────┘
```

## Files

| File | Description |
|------|-------------|
| `task-definition.json` | ECS Task Definition |
| `cloudformation-template.yml` | Infrastructure as Code |
| `../Dockerfile.prod` | Production Docker image |
| `../.github/workflows/ci-cd.yml` | CI/CD Pipeline |

## Environment Variables (Secrets Manager)

| Secret | Description |
|--------|-------------|
| `mattilda/database-url` | PostgreSQL connection string |
| `mattilda/redis-url` | Redis connection string |
| `mattilda/secret-key` | JWT signing key |

## Commands

### Deploy Infrastructure (CloudFormation)
```bash
aws cloudformation deploy \
  --template-file cloudformation-template.yml \
  --stack-name mattilda-infrastructure \
  --parameter-overrides Environment=staging \
  --capabilities CAPABILITY_IAM
```

### Manual Deploy to ECS
```bash
# Build and push image
docker build -t mattilda-backend -f Dockerfile.prod .
docker tag mattilda-backend:latest ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/mattilda-backend:latest
docker push ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/mattilda-backend:latest

# Update service
aws ecs update-service --cluster mattilda-cluster-prod --service mattilda-api-service --force-new-deployment
```

### View Logs
```bash
aws logs tail /ecs/mattilda-api --follow
```

## Cost Estimation (Monthly)

| Service | Staging | Production |
|---------|---------|------------|
| ECS Fargate (2 tasks) | ~$30 | ~$60 |
| RDS t3.micro | ~$15 | ~$30 (Multi-AZ) |
| ElastiCache t3.micro | ~$12 | ~$12 |
| ALB | ~$20 | ~$20 |
| **Total** | **~$77** | **~$122** |

## Security Best Practices

1. **Secrets**: All sensitive data stored in AWS Secrets Manager
2. **Network**: Private subnets for databases, public only for ALB
3. **IAM**: Least privilege roles for ECS tasks
4. **Encryption**: TLS for ALB, encryption at rest for RDS
5. **Scanning**: ECR image scanning enabled
