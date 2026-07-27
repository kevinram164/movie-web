"""OpenTelemetry tracing for media-worker — CONSUMER spans for Redis jobs (Instana)."""

from __future__ import annotations

import os
from contextlib import nullcontext


def init_tracing(service_name: str = "media-worker") -> None:
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()
    if not endpoint:
        return
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import SERVICE_NAME, Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        name = os.getenv("OTEL_SERVICE_NAME", service_name).strip() or service_name
        provider = TracerProvider(resource=Resource.create({SERVICE_NAME: name}))
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(insecure=True)))
        trace.set_tracer_provider(provider)

        try:
            from opentelemetry.instrumentation.redis import RedisInstrumentor

            RedisInstrumentor().instrument()
        except Exception:
            pass

        try:
            from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
            from worker import db

            if getattr(db, "engine", None):
                SQLAlchemyInstrumentor().instrument(engine=db.engine)
        except Exception:
            pass
    except Exception:
        pass


def get_tracer(service_name: str = "media-worker"):
    try:
        from opentelemetry import trace

        return trace.get_tracer(service_name, "1.0")
    except Exception:
        return None


def consumer_span(tracer, name: str, attributes: dict | None = None):
    """Redis queue consumer — Instana maps CONSUMER spans to services."""
    if not tracer:
        return nullcontext()
    from opentelemetry.trace import SpanKind

    attrs = {"messaging.system": "redis", "messaging.operation": "process"}
    if attributes:
        attrs.update(attributes)
    return tracer.start_as_current_span(name, kind=SpanKind.CONSUMER, attributes=attrs)
