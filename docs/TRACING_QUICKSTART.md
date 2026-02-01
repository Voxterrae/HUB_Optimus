# Quick Start: OpenTelemetry Tracing

This guide will help you get started with tracing in the HUB_Optimus agent workspace.

## Prerequisites

- Python 3.12+
- Dependencies installed: `pip install -r requirements.txt`

## Quick Start Steps

### 1. Enable Tracing

Copy `.env.example` to `.env` if you haven't already:

```bash
cp .env.example .env
```

Enable tracing by editing your `.env` file:

```bash
TRACING_ENABLED=true
TRACING_CONSOLE=true
```

### 2. Run the Agent

Start the agent using VS Code's debug configuration or directly:

```bash
python -m debugpy --listen 127.0.0.1:5679 -m agentdev run agent/app.py --verbose --port 8087
```

### 3. Verify Tracing

You should see console output similar to:

```
OpenTelemetry tracing initialized
```

And trace spans will be printed to the console as JSON when operations occur.

## What Gets Traced?

The tracing system captures:

- Agent initialization and setup
- Request processing
- Azure AI service interactions
- Custom operations (when instrumented)

## Next Steps

- **Production Setup**: Configure OTLP endpoint for production monitoring
- **Advanced Configuration**: See [docs/TRACING.md](./TRACING.md) for detailed options
- **Integration**: Connect to Jaeger, Zipkin, Azure Monitor, or other backends
- **Custom Spans**: Add your own tracing spans in agent code

## Disabling Tracing

Set in your `.env`:

```bash
TRACING_ENABLED=false
```

Or remove the variable entirely. The agent will work normally without tracing.

## Troubleshooting

**Problem**: "OpenTelemetry tracing initialized" not showing

**Solution**: 
1. Check that `TRACING_ENABLED=true` in your `.env` file
2. Ensure the `.env` file is in the repository root
3. Verify dependencies are installed: `pip install -r requirements.txt`

**Problem**: No trace output appearing

**Solution**:
1. Enable console output: `TRACING_CONSOLE=true`
2. Check that operations are actually occurring (make requests to the agent)
3. Check for error messages during startup

## Support

For detailed documentation, see [docs/TRACING.md](./TRACING.md)
