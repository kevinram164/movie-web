"""OpenTelemetry tracing — OTLP → shared collector → Coroot + Instana (same as banking)."""

from __future__ import annotations

import os
import sys


def _log(msg: str) -> None:
    # Always visible in uvicorn/container logs (no logging config needed)
    print(f"[otel] {msg}", file=sys.stderr, flush=True)


def init_tracing(service_name: str) -> None:
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()
    if not endpoint:
        _log("disabled: OTEL_EXPORTER_OTLP_ENDPOINT empty")
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
        except Exception as exc:  # noqa: BLE001
            _log(f"redis instrument skip: {exc}")

        try:
            from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
            from app import db

            if getattr(db, "engine", None):
                SQLAlchemyInstrumentor().instrument(engine=db.engine)
        except Exception as exc:  # noqa: BLE001
            _log(f"sqlalchemy instrument skip: {exc}")

        _log(f"tracing enabled service={name} endpoint={endpoint}")
    except Exception as exc:  # noqa: BLE001
        _log(f"init FAILED: {exc}")


def instrument_fastapi(app, service_name: str) -> None:
    init_tracing(service_name)
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(app)
        _log(f"fastapi instrumented service={service_name}")
    except Exception as exc:  # noqa: BLE001
        _log(f"fastapi instrument FAILED: {exc}")
