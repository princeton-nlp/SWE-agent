import functools
import inspect
from typing import List
from opentelemetry import trace
from opentelemetry.sdk.resources import SERVICE_NAME, Resource, Attributes
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
)

from sweagent.utils.config import keys_config

# re-export this from here so we don't have to litter the code with otel imports
Tracer = trace.Tracer

_tracer = None


def tracer() -> Tracer:
    global _tracer

    if _tracer is None:
        # warn about tracer being uninitialized but don't fail here - instead return a NoOpProvider tracer (tests seem to hit this.)
        print("WARNING: tracer not initialized.  Returning NoOpProvider tracer.")
        _tracer = trace.get_tracer_provider().get_tracer("replayio.ai_playground")

    return _tracer


def set_tracer(tracer: Tracer):
    global _tracer
    _tracer = tracer


def current_span() -> trace.Span:
    return trace.get_current_span()


# Creates a tracer from the global tracer provider
def initialize_tracer(attributes: Attributes | None = None):
    service_resource = Resource.create(
        {
            SERVICE_NAME: "SWE-agent",
        }
    )

    extra_resource = (
        Resource.get_empty() if attributes is None else Resource.create(attributes)
    )

    exporter = None
    api_key = keys_config.get("HONEYCOMB_API_KEY")
    otlp_endpoint = keys_config.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    if api_key is not None and otlp_endpoint is not None:
        # TODO(toshok): this is for grpc, which I'd love to use, but doesn't seem to work?
        # exporter = OTLPSpanExporter(
        #     endpoint=keys_config.get("OTEL_EXPORTER_OTLP_ENDPOINT"),
        #     headers=(("x-honeycomb-team", api_key)),
        # )
        exporter = OTLPSpanExporter(
            endpoint=otlp_endpoint,
            headers={
                "x-honeycomb-team": api_key,
            },
        )

    if exporter is None:
        provider = trace.NoOpTracerProvider()
    else:
        provider = TracerProvider(resource=extra_resource.merge(service_resource))
        processor = BatchSpanProcessor(exporter)
        provider.add_span_processor(processor)

    # Sets the global default tracer provider
    trace.set_tracer_provider(provider)

    set_tracer(trace.get_tracer("SWE-agent"))

def instrument(
    name: str, params: List[str] | None = None, attributes: Attributes | None = None
):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            span_attributes = {}

            if params:
                sig = inspect.signature(func)
                bound_args = sig.bind(*args, **kwargs)
                bound_args.apply_defaults()

                include_all_kwargs = "kwargs" in params
                kwargs_to_include = [
                    p.split(".")[1] for p in params if p.startswith("kwargs.")
                ]

                for param in params:
                    if param == "kwargs" or param.startswith("kwargs."):
                        # we'll handle these below
                        continue
                    elif param in bound_args.arguments:
                        span_attributes[param] = bound_args.arguments[param]

                # Handle kwargs
                if include_all_kwargs or kwargs_to_include:
                    for k, v in bound_args.arguments.get("kwargs", {}).items():
                        if include_all_kwargs or k in kwargs_to_include:
                            span_attributes[f"kwarg.{k}"] = v

            if attributes:
                span_attributes.update(attributes)

            with tracer().start_as_current_span(name, attributes=span_attributes):
                return func(*args, **kwargs)

        return wrapper

    return decorator


__all__ = [
    "current_span",
    "initialize_tracer",
    "instrument",
    "tracer",
]
