#!/bin/bash
set -e

echo "=========================================="
echo "ER_CHAI Lightsail Setup Script"
echo "=========================================="
echo ""

# Update system
echo "Step 1/6: Updating system packages..."
sudo yum update -y

# Install Docker
echo "Step 2/6: Installing Docker..."
sudo yum install -y docker
sudo service docker start
sudo usermod -a -G docker $USER

# Install Docker Compose
echo "Step 3/6: Installing Docker Compose..."
DOCKER_COMPOSE_VERSION="v2.24.5"
sudo curl -L "https://github.com/docker/compose/releases/download/${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installations
echo "Step 4/6: Verifying installations..."
docker --version
docker-compose --version

# Clone repository (if not already cloned)
echo "Step 5/6: Setting up repository..."
if [ ! -d "ER_CHAI" ]; then
    echo "Cloning repository..."
    git clone https://github.com/tjblavakumar/ER_CHAI.git
    cd ER_CHAI/deployment/lightsail
else
    echo "Repository already exists. Updating..."
    cd ER_CHAI
    git pull origin main
    cd deployment/lightsail
fi

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
fi

# Create config.yaml file if it doesn't exist
if [ ! -f "config.yaml" ]; then
    echo "Creating config.yaml file from template..."
    cp config.yaml.example config.yaml
    echo "⚠️  IMPORTANT: Edit config.yaml and add your credentials!"
    echo "   Run: nano config.yaml"
    echo "   Required: FRED API key"
    echo "   Optional: AWS credentials (if not using IAM role)"
fi

# Build and start containers
echo "Step 6/6: Building and starting containers..."
echo "This may take 5-10 minutes on first run..."
docker-compose up -d --build

# Wait for services to be healthy
echo ""
echo "Waiting for services to start..."
sleep 10

# Get public IP
PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)

echo ""
echo "=========================================="
echo "✅ Setup Complete!"
echo "=========================================="
echo ""
echo "Your ER_CHAI application is now running at:"
echo "  http://${PUBLIC_IP}"
echo ""
echo "Useful commands:"
echo "  ./manage.sh status   - Check service status"
echo "  ./manage.sh logs     - View logs"
echo "  ./manage.sh stop     - Stop services"
echo "  ./manage.sh start    - Start services"
echo "  ./manage.sh restart  - Restart services"
echo ""
echo "⚠️  Don't forget to:"
echo "  1. Configure AWS credentials in .env file"
echo "  2. Attach IAM role with Bedrock permissions to this instance"
echo "  3. Open port 80 in Lightsail firewall"
echo ""
