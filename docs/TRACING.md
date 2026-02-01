# OpenTelemetry Tracing for HUB_Optimus Agent

This document describes how to configure and use OpenTelemetry tracing for the HUB_Optimus agent.

## Overview

The agent now includes OpenTelemetry tracing support, which provides observability into agent operations, performance metrics, and execution flow. This is particularly useful when working with AI Toolkit Agent Inspector and debugging agent behavior.

## Configuration

Tracing is configured through environment variables in your `.env` file. See `.env.example` for all available options.

### Basic Configuration

To enable tracing, set the following in your `.env` file:

```bash
TRACING_ENABLED=true
```

**Note**: When tracing is enabled without specifying an exporter, it defaults to console output for immediate feedback during development.

### Console Tracing (Local Development)

For local development, you can explicitly enable console output:

```bash
TRACING_ENABLED=true
TRACING_CONSOLE=true
```

This will print span information to the console as the agent runs, useful for immediate debugging. Console output is also the default when tracing is enabled without configuring any other exporter.

### OTLP Exporter (Production/Integration)

To send traces to an OpenTelemetry Collector or compatible backend:

```bash
TRACING_ENABLED=true
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
```

For authenticated endpoints, you can add headers:

```bash
OTEL_EXPORTER_OTLP_HEADERS=authorization=Bearer YOUR_TOKEN,x-custom-header=value
```

### Additional Configuration

```bash
SERVICE_VERSION=1.0.0                    # Service version for tracing
DEPLOYMENT_ENVIRONMENT=development       # Environment name (development, staging, production)
```

## Usage with AI Toolkit Agent Inspector

When running the agent with AI Toolkit Agent Inspector, tracing will automatically capture:

- Agent initialization and configuration
- Request handling and processing
- Azure AI service calls
- Error conditions and exceptions

To view traces in the Agent Inspector:

1. Enable tracing in your `.env` file
2. Start the agent using the "Debug Local Agent HTTP Server" configuration
3. The Agent Inspector will display trace information alongside other debugging data

## Integration with OpenTelemetry Backends

The agent supports any OpenTelemetry-compatible backend, including:

- **Jaeger**: Distributed tracing platform
- **Zipkin**: Distributed tracing system
- **Azure Monitor**: Microsoft's application monitoring service
- **Datadog**: Application monitoring and analytics
- **New Relic**: Application performance monitoring

Configure the `OTEL_EXPORTER_OTLP_ENDPOINT` to point to your chosen backend's OTLP endpoint.

## Example: Using Jaeger Locally

1. Run Jaeger in a Docker container:

```bash
docker run -d --name jaeger \
  -e COLLECTOR_OTLP_ENABLED=true \
  -p 16686:16686 \
  -p 4317:4317 \
  jaegertracing/all-in-one:latest
```

2. Configure your `.env`:

```bash
TRACING_ENABLED=true
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
```

3. Run your agent and view traces at http://localhost:16686

## Disabling Tracing

To disable tracing (default behavior):

```bash
TRACING_ENABLED=false
```

Or simply omit the `TRACING_ENABLED` variable from your `.env` file.

## Architecture

The tracing implementation consists of:

- **`agent/tracing.py`**: Tracing configuration and setup module
- **`agent/app.py`**: Agent application with tracing initialization
- **Environment variables**: Configuration through `.env` file

The setup is non-intrusive and only activates when explicitly enabled, ensuring no performance impact in production unless needed.

## Troubleshooting

### Traces not appearing

1. Verify `TRACING_ENABLED=true` in your `.env` file
2. Check that the OTLP endpoint is accessible
3. Enable console tracing to verify spans are being created
4. Check for error messages during agent startup

### Performance impact

- Tracing has minimal overhead when disabled (default)
- When enabled, spans are batched and exported asynchronously
- Console tracing may impact performance in high-throughput scenarios

## Further Reading

- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)
- [OpenTelemetry Python](https://opentelemetry.io/docs/instrumentation/python/)
- [AI Toolkit Agent Inspector](https://learn.microsoft.com/en-us/ai/)
