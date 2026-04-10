# ER_CHAI - Quick Deployment Guide

## 🚀 Deploy to AWS Lightsail in 10 Minutes

### Step 1: Create Lightsail Instance (2 minutes)

1. Go to https://lightsail.aws.amazon.com/
2. Click **Create Instance**
3. Choose:
   - **OS**: Amazon Linux 2023
   - **Plan**: $10/month (2GB RAM)
4. Click **Create**

### Step 2: Configure Firewall (1 minute)

1. Go to **Networking** tab
2. Add firewall rule:
   - **Application**: HTTP
   - **Port**: 80

### Step 3: Attach IAM Role for Bedrock (2 minutes)

1. Stop your Lightsail instance
2. Go to AWS EC2 Console
3. Find your instance → Actions → Security → Modify IAM role
4. Create/select role with `AmazonBedrockFullAccess`
5. Start instance

### Step 4: Deploy (5 minutes)

1. Click **Connect using SSH** in Lightsail Console

2. Run this one command:

```bash
curl -o setup.sh https://raw.githubusercontent.com/tjblavakumar/ER_CHAI/main/deployment/lightsail/setup.sh && chmod +x setup.sh && ./setup.sh
```

3. Wait 5-10 minutes for build to complete

### Step 5: Access Your App

Open browser: `http://<YOUR-LIGHTSAIL-IP>`

Find your IP in the Lightsail Console.

---

## 📋 Daily Management

```bash
cd ~/ER_CHAI/deployment/lightsail

# Check status
./manage.sh status

# View logs
./manage.sh logs

# Restart
./manage.sh restart

# Update app
./manage.sh update
```

---

## 💰 Cost Management

**Stop instance when not in use:**
1. Lightsail Console → Select instance
2. Click ⋮ → Stop

**Costs:**
- Running: $10/month
- Stopped: ~$2/month (storage only)

---

## 🔧 Troubleshooting

**App not loading?**
```bash
./manage.sh status
./manage.sh logs
```

**Need to restart?**
```bash
./manage.sh restart
```

**Update code from GitHub?**
```bash
./manage.sh update
```

---

## 📚 Full Documentation

See [deployment/README.md](./README.md) for complete guide.

---

## ✅ What You Get

- ✅ Public URL accessible by your team
- ✅ Auto-restart on instance reboot
- ✅ One-click stop/start from AWS Console
- ✅ Easy updates with `./manage.sh update`
- ✅ Minimal infrastructure ($10/month)
