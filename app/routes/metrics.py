import json
import time
from datetime import datetime
from fastapi import APIRouter
from fastapi.responses import Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, REGISTRY

router = APIRouter(prefix="/metrics", tags=["Metrics"])


@router.get("/prometheus")
def prometheus_metrics():
    """Prometheus metrics endpoint in Prometheus format."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@router.get("/json")
def registry_to_json():
    """AI and system metrics in JSON format with timestamps."""
    current_time = time.time()
    metrics_data = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "epoch_timestamp": int(current_time),
        "metrics": [],
        "prometheus_queries": {
            "average_latency": "rate(ai_request_duration_seconds_sum[5m]) / rate(ai_request_duration_seconds_count[5m])",
            "p95_latency": "histogram_quantile(0.95, rate(ai_request_duration_seconds_bucket[5m]))",
            "p99_latency": "histogram_quantile(0.99, rate(ai_request_duration_seconds_bucket[5m]))",
            "request_rate": "rate(ai_requests_total[5m])",
            "error_rate": "rate(ai_errors_total[5m]) / rate(ai_requests_total[5m])"
        }
    }

    for metric_family in REGISTRY.collect():
        family_info = {
            "name": metric_family.name,
            "documentation": metric_family.documentation,
            "type": metric_family.type,
            "samples": []
        }

        for sample in metric_family.samples:
            family_info["samples"].append({
                "name": sample.name,
                "labels": sample.labels,
                "value": sample.value,
                "timestamp": sample.timestamp if sample.timestamp else current_time
            })

        metrics_data["metrics"].append(family_info)

    return metrics_data
