"""OpenTelemetry tracing for media-worker — CONSUMER spans for Redis jobs (Instana)."""

from __future__ import annotations

import os
import threading
import time
from contextlib import nullcontext

_heartbeat_started: set[str] = set()


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

        start_heartbeat(name)
    except Exception:
        pass


def start_heartbeat(service_name: str) -> None:
    """Periodic SERVER span so Instana keeps media-worker visible without jobs."""
    if not os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip():
        return
    if os.getenv("OTEL_HEARTBEAT", "1").strip().lower() in ("0", "false", "no", "off"):
        return
    if service_name in _heartbeat_started:
        return
    _heartbeat_started.add(service_name)
    try:
        interval = max(10, int(os.getenv("OTEL_HEARTBEAT_SECONDS", "30")))
    except ValueError:
        interval = 30
    tracer = get_tracer(service_name)
    if not tracer:
        return

    def _loop() -> None:
        from opentelemetry.trace import SpanKind, Status, StatusCode

        while True:
            try:
                with tracer.start_as_current_span(
                    "otel.heartbeat",
                    kind=SpanKind.SERVER,
                    attributes={"heartbeat": True, "http.route": "/__heartbeat__"},
                ) as span:
                    span.set_status(Status(StatusCode.OK))
            except Exception:
                pass
            time.sleep(interval)

    threading.Thread(target=_loop, name=f"otel-hb-{service_name}", daemon=True).start()


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
