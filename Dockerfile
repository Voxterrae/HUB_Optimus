# Use official Python runtime as base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy agent code
COPY agent/ ./agent/

# Copy environment file template
COPY .env.example ./.env.example

# Expose port for the agent server
EXPOSE 8087

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run the agent with agentdev
CMD ["python", "-m", "agentdev", "run", "agent/app.py", "--port", "8087"]
