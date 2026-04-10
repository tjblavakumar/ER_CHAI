# ER_CHAI Deployment Guide

This directory contains deployment configurations for the ER_CHAI application.

## Quick Start - AWS Lightsail

Deploy ER_CHAI to AWS Lightsail in ~10 minutes.

### Prerequisites

- AWS Account
- AWS Lightsail instance (recommended: 2GB RAM or higher)
- GitHub repository access

### Step 1: Create Lightsail Instance

1. Go to [AWS Lightsail Console](https://lightsail.aws.amazon.com/)
2. Click **Create Instance**
3. Select:
   - **Platform**: Linux/Unix
   - **Blueprint**: OS Only → Amazon Linux 2023
   - **Instance Plan**: $10/month (2GB RAM, 1 vCPU) or higher
   - **Instance Name**: `er-chai-app`
4. Click **Create Instance**
5. Wait for instance to start (Status: Running)

### Step 2: Configure Networking

1. In your instance page, go to **Networking** tab
2. Under **IPv4 Firewall**, add rule:
   - **Application**: HTTP
   - **Protocol**: TCP
   - **Port**: 80
3. (Optional) Create a **Static IP**:
   - Click **Create static IP**
   - Attach to your instance
   - Note the IP address

### Step 3: Attach IAM Role for AWS Bedrock

1. Go to [AWS IAM Console](https://console.aws.amazon.com/iam/)
2. Create a new role:
   - **Trusted entity**: EC2
   - **Permissions**: `AmazonBedrockFullAccess` (or create custom policy)
   - **Role name**: `LightsailBedrockRole`
3. Go back to Lightsail Console
4. Stop your instance
5. In AWS EC2 Console, find your Lightsail instance
6. Actions → Security → Modify IAM role
7. Select `LightsailBedrockRole`
8. Start instance again

### Step 4: SSH and Deploy

1. In Lightsail Console, click **Connect using SSH** (browser-based terminal)

2. Run the setup script:

```bash
# Download and run setup script
curl -o setup.sh https://raw.githubusercontent.com/tjblavakumar/ER_CHAI/main/deployment/lightsail/setup.sh
chmod +x setup.sh
./setup.sh
```

3. The script will:
   - Install Docker and Docker Compose
   - Clone the repository
   - Build containers
   - Start the application

4. Wait 5-10 minutes for initial build

### Step 5: Access Your Application

Open your browser and navigate to:
```
http://<YOUR-LIGHTSAIL-IP>
```

You can find your IP in the Lightsail Console.

## Management

### Daily Operations

```bash
# Navigate to deployment directory
cd ~/ER_CHAI/deployment/lightsail

# Check service status
./manage.sh status

# View logs
./manage.sh logs

# Restart services
./manage.sh restart

# Stop services
./manage.sh stop

# Start services
./manage.sh start
```

### Update Application

When you push new code to GitHub:

```bash
cd ~/ER_CHAI/deployment/lightsail
./manage.sh update
```

This will:
1. Pull latest code from GitHub
2. Rebuild containers
3. Restart services

### View Logs

```bash
# All logs
./manage.sh logs

# Backend only
./manage.sh logs-backend

# Frontend only
./manage.sh logs-frontend
```

### Troubleshooting

```bash
# Check container status
docker ps

# Access backend shell
./manage.sh shell-backend

# Access frontend shell
./manage.sh shell-frontend

# Check Docker logs
docker logs er_chai_backend
docker logs er_chai_frontend
```

## Stop/Start Instance (Cost Saving)

### From Lightsail Console:

1. Select your instance
2. Click **⋮** (three dots) → **Stop**
3. To restart: Click **⋮** → **Start**

**Note**: Containers will auto-start when instance boots up (configured with `restart: unless-stopped`)

### Cost When Stopped:

- Compute: $0/month
- Storage: ~$2/month (for 20GB disk)
- Static IP: $0 (if attached to instance)

## Architecture

```
┌─────────────────────────────────────────┐
│         AWS Lightsail Instance          │
│                                         │
│  ┌───────────────────────────────────┐ │
│  │      Docker Compose               │ │
│  │                                   │ │
│  │  ┌──────────┐    ┌─────────────┐ │ │
│  │  │ Frontend │    │   Backend   │ │ │
│  │  │  (Nginx) │───▶│  (FastAPI)  │ │ │
│  │  │  Port 80 │    │  Port 8080  │ │ │
│  │  └──────────┘    └─────────────┘ │ │
│  │                         │         │ │
│  │                    ┌────▼─────┐   │ │
│  │                    │  SQLite  │   │ │
│  │                    │   (DB)   │   │ │
│  │                    └──────────┘   │ │
│  └───────────────────────────────────┘ │
│                                         │
│  IAM Role: Bedrock Access               │
└─────────────────────────────────────────┘
                  │
                  ▼
         http://<PUBLIC-IP>
```

## Configuration

The application uses `config.yaml` for configuration. After deployment, you need to edit it:

```bash
cd ~/ER_CHAI/deployment/lightsail
nano config.yaml
```

### Required Configuration

1. **FRED API Key** (required for economic data):
   ```yaml
   fred_api_key: YOUR_FRED_API_KEY_HERE
   ```
   Get your free key at: https://fred.stlouisfed.org/docs/api/api_key.html

2. **AWS Credentials** (choose one method):

   **Method A: IAM Role (Recommended)**
   - If you attached IAM role to Lightsail instance, leave AWS credentials commented out
   - The application will automatically use the instance role
   
   **Method B: Access Keys**
   - Uncomment and fill in:
   ```yaml
   aws_access_key_id: YOUR_ACCESS_KEY_HERE
   aws_secret_access_key: YOUR_SECRET_KEY_HERE
   ```

### After Editing config.yaml

Restart the services:
```bash
./manage.sh restart
```

## Security Best Practices

1. **Use IAM Role** instead of AWS credentials in `.env`
2. **Enable HTTPS** (optional):
   - Use Lightsail load balancer with SSL certificate
   - Or use Cloudflare for free SSL
3. **Restrict SSH access**:
   - In Lightsail Firewall, change SSH source to "My IP"
4. **Regular updates**:
   ```bash
   sudo yum update -y
   docker-compose pull
   ```

## Monitoring

### Check Application Health

```bash
# Health check endpoint
curl http://localhost/health

# Backend API health
curl http://localhost:8080/api/health
```

### Resource Usage

```bash
# Container stats
docker stats

# Disk usage
df -h

# Memory usage
free -h
```

## Backup

### Backup Database

```bash
# Copy SQLite database
docker cp er_chai_backend:/app/data/projects.db ~/backup-$(date +%Y%m%d).db

# Download to local machine
scp -i your-key.pem ec2-user@<IP>:~/backup-*.db ./
```

### Restore Database

```bash
# Upload backup
scp -i your-key.pem ./backup.db ec2-user@<IP>:~/

# Restore
docker cp ~/backup.db er_chai_backend:/app/data/projects.db
./manage.sh restart
```

## Estimated Costs

| Instance Plan | RAM | vCPU | Storage | Monthly Cost |
|--------------|-----|------|---------|--------------|
| $10/month    | 2GB | 1    | 40GB    | $10          |
| $20/month    | 4GB | 2    | 80GB    | $20          |
| $40/month    | 8GB | 2    | 160GB   | $40          |

**Additional costs**:
- Data transfer: First 1TB free, then $0.09/GB
- Static IP: Free (if attached)
- Bedrock API: Pay per use (~$0.003 per 1K tokens)

## Troubleshooting

### Application not accessible

1. Check firewall: Port 80 should be open
2. Check containers: `docker ps`
3. Check logs: `./manage.sh logs`

### Backend errors

1. Check IAM role is attached
2. Check AWS region in `.env`
3. View backend logs: `./manage.sh logs-backend`

### Out of memory

1. Upgrade to larger instance plan
2. Check container stats: `docker stats`

### Slow performance

1. Upgrade instance (more RAM/CPU)
2. Check Docker resource usage
3. Consider using Lightsail Container Service for auto-scaling

## Support

For issues or questions:
- GitHub Issues: https://github.com/tjblavakumar/ER_CHAI/issues
- Email: tjblavakumar@gmail.com
