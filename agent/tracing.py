"""OpenTelemetry tracing configuration for HUB_Optimus agent."""

import os
from typing import Optional

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter


def setup_tracing(service_name: str = "hub-optimus-agent") -> Optional[trace.Tracer]:
    """
    Configure OpenTelemetry tracing for the agent.
    
    Args:
        service_name: Name of the service for tracing identification
        
    Returns:
        Configured tracer instance or None if tracing is disabled
    """
    # Check if tracing is enabled
    tracing_enabled = os.getenv("TRACING_ENABLED", "false").lower() == "true"
    if not tracing_enabled:
        return None
    
    # Create resource with service information
    resource = Resource.create(
        {
            "service.name": service_name,
            "service.version": os.getenv("SERVICE_VERSION", "1.0.0"),
            "deployment.environment": os.getenv("DEPLOYMENT_ENVIRONMENT", "development"),
        }
    )
    
    # Create tracer provider
    provider = TracerProvider(resource=resource)
    
    # Configure exporters based on environment
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    console_tracing = os.getenv("TRACING_CONSOLE", "false").lower() == "true"
    
    if otlp_endpoint:
        # OTLP exporter for production/integration
        otlp_exporter = OTLPSpanExporter(
            endpoint=otlp_endpoint,
            headers=_get_otlp_headers(),
        )
        provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
    
    if console_tracing:
        # Console exporter for local development
        console_exporter = ConsoleSpanExporter()
        provider.add_span_processor(BatchSpanProcessor(console_exporter))
    
    # Set as global tracer provider
    trace.set_tracer_provider(provider)
    
    # Return tracer instance
    return trace.get_tracer(__name__)


def _get_otlp_headers() -> dict:
    """
    Get headers for OTLP exporter from environment variables.
    
    Returns:
        Dictionary of headers for authentication/authorization
    """
    headers = {}
    
    # Support for custom headers via OTEL_EXPORTER_OTLP_HEADERS
    headers_env = os.getenv("OTEL_EXPORTER_OTLP_HEADERS", "")
    if headers_env:
        for header in headers_env.split(","):
            if "=" in header:
                key, value = header.split("=", 1)
                headers[key.strip()] = value.strip()
    
    return headers


def get_tracer() -> trace.Tracer:
    """
    Get the current tracer instance.
    
    Returns:
        Current tracer from the global tracer provider
    """
    return trace.get_tracer(__name__)
