# Deployment to Azure AI Foundry

This guide explains how to deploy the HUB_Optimus agent to Azure AI Foundry.

## Prerequisites

1. **Azure Subscription**: You need an active Azure subscription.
2. **Azure Developer CLI (azd)**: Install from https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd
3. **Azure CLI**: Install from https://docs.microsoft.com/cli/azure/install-azure-cli
4. **Docker Desktop**: Required for local testing (optional but recommended).
5. **Azure AI Foundry Project**: Create a project in Azure AI Foundry portal.

## Environment Setup

1. **Create a `.env` file** based on `.env.example`:
   ```bash
   cp .env.example .env
   ```

2. **Configure environment variables** in `.env`:
   ```
   FOUNDRY_PROJECT_ENDPOINT=https://your-project.api.azureml.ms
   FOUNDRY_MODEL_DEPLOYMENT_NAME=your-model-deployment-name
   AGENT_NAME=HUB-Optimus-Agent
   AGENT_INSTRUCTIONS=You are HUB_Optimus, a careful, integrity-first simulation assistant. Help users explore scenarios, clarify incentives, and evaluate verification steps.
   ```

   To get these values:
   - Go to Azure AI Foundry portal (https://ai.azure.com)
   - Select your project
   - Copy the project endpoint from the project settings
   - Note your model deployment name from the deployments section

## Deployment Steps

### Option 1: Deploy with Azure Developer CLI (Recommended)

1. **Login to Azure**:
   ```bash
   azd auth login
   ```

2. **Initialize the deployment** (first time only):
   ```bash
   azd init
   ```
   - Accept the defaults or customize as needed
   - This will use the `azure.yaml` configuration

3. **Set environment variables** for the deployment:
   ```bash
   azd env set FOUNDRY_PROJECT_ENDPOINT "your-endpoint"
   azd env set FOUNDRY_MODEL_DEPLOYMENT_NAME "your-deployment-name"
   azd env set AGENT_NAME "HUB-Optimus-Agent"
   azd env set AGENT_INSTRUCTIONS "You are HUB_Optimus..."
   ```

4. **Deploy to Azure**:
   ```bash
   azd up
   ```
   This will:
   - Provision Azure resources (if needed)
   - Build the Docker container
   - Push the container to Azure Container Registry
   - Deploy the agent to Azure Container Apps

5. **For subsequent updates**, use:
   ```bash
   azd deploy
   ```

### Option 2: Manual Docker Deployment

1. **Build the Docker image**:
   ```bash
   docker build -t hub-optimus-agent .
   ```

2. **Test locally**:
   ```bash
   docker run -p 8087:8087 --env-file .env hub-optimus-agent
   ```

3. **Push to Azure Container Registry** (replace with your registry name):
   ```bash
   az acr login --name your-registry
   docker tag hub-optimus-agent your-registry.azurecr.io/hub-optimus-agent:latest
   docker push your-registry.azurecr.io/hub-optimus-agent:latest
   ```

4. **Deploy to Container Apps** using Azure Portal or CLI.

## Local Testing

### Option 1: Test with Docker

```bash
docker build -t hub-optimus-agent .
docker run -p 8087:8087 --env-file .env hub-optimus-agent
```

### Option 2: Test with VS Code AI Toolkit

1. Open the project in VS Code
2. Ensure you have the AI Toolkit extension installed
3. Press F5 or use the "Debug Local Agent HTTP Server" configuration
4. The Agent Inspector will open automatically

## Monitoring and Debugging

After deployment:

1. **View logs**:
   ```bash
   azd logs
   ```

2. **Check deployment status**:
   ```bash
   azd show
   ```

3. **Access the agent endpoint**:
   - The deployment will output the agent's URL
   - You can interact with it via HTTP requests

## Troubleshooting

### Common Issues

1. **Authentication errors**: Ensure you're logged in with `azd auth login` and `az login`
2. **Environment variables not set**: Double-check your `.env` file or `azd env` settings
3. **Docker build fails**: Ensure all dependencies in `requirements.txt` are compatible
4. **Port conflicts**: If port 8087 is in use, modify the port in Dockerfile and azure.yaml

## CI/CD Integration

To automate deployments with GitHub Actions:

1. Create Azure service principal:
   ```bash
   azd pipeline config
   ```

2. This will:
   - Create a service principal
   - Set up GitHub secrets
   - Generate a workflow file

3. The agent will automatically deploy on push to main branch

## Additional Resources

- [Azure AI Foundry Documentation](https://learn.microsoft.com/azure/ai-foundry/)
- [Azure Developer CLI Documentation](https://learn.microsoft.com/azure/developer/azure-developer-cli/)
- [Deploy hosted agents](https://learn.microsoft.com/azure/ai-foundry/agents/how-to/deploy-hosted-agent)

## Security Notes

- Never commit `.env` files with real credentials
- Use Azure Key Vault for production secrets
- Review the security settings in Azure Portal
- Enable authentication for production deployments
