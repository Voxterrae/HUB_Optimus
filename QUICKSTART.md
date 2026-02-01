# Quick Start: Deploy to Azure AI Foundry

This is a quick reference for deploying HUB_Optimus to Azure AI Foundry. For detailed instructions, see [DEPLOYMENT.md](DEPLOYMENT.md).

## Prerequisites
- Azure subscription
- Azure Developer CLI (azd) installed: https://aka.ms/azd-install
- Docker Desktop (for local testing)

## Quick Deploy (5 steps)

### 1. Login to Azure
```bash
azd auth login
```

### 2. Set up environment
Create a `.env` file:
```bash
cp .env.example .env
```

Edit `.env` with your Azure AI Foundry details:
```
FOUNDRY_PROJECT_ENDPOINT=https://your-project.api.azureml.ms
FOUNDRY_MODEL_DEPLOYMENT_NAME=your-model-deployment-name
```

Get these from: https://ai.azure.com → Your Project → Settings

### 3. Initialize deployment
```bash
azd init
```
Accept defaults when prompted.

### 4. Configure environment variables
```bash
azd env set FOUNDRY_PROJECT_ENDPOINT "your-endpoint"
azd env set FOUNDRY_MODEL_DEPLOYMENT_NAME "your-deployment"
```

### 5. Deploy!
```bash
azd up
```

This will:
- ✓ Build the Docker container
- ✓ Push to Azure Container Registry
- ✓ Deploy to Azure Container Apps
- ✓ Configure networking and scaling

## Update deployed app
After making code changes:
```bash
azd deploy
```

## View logs
```bash
azd logs
```

## Test locally first
```bash
docker build -t hub-optimus-agent .
docker run -p 8087:8087 --env-file .env hub-optimus-agent
```

## Need help?
- Full guide: [DEPLOYMENT.md](DEPLOYMENT.md)
- Azure AI Foundry docs: https://learn.microsoft.com/azure/ai-foundry/
- Issues: https://github.com/Voxterrae/HUB_Optimus/issues
