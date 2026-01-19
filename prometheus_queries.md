# Prometheus Latency Queries

## Understanding Histogram Metrics

When you see `ai_request_duration_seconds` with `le` labels, these are histogram buckets:
- `le="0.1"` = requests that took ≤ 0.1 seconds
- `le="0.5"` = requests that took ≤ 0.5 seconds  
- `le="1.0"` = requests that took ≤ 1.0 seconds
- `le="+Inf"` = all requests (total count)

## Useful Prometheus Queries for Latency

### Average Latency
```promql
rate(ai_request_duration_seconds_sum[5m]) / rate(ai_request_duration_seconds_count[5m])
```

### 95th Percentile Latency
```promql
histogram_quantile(0.95, rate(ai_request_duration_seconds_bucket[5m]))
```

### 99th Percentile Latency
```promql
histogram_quantile(0.99, rate(ai_request_duration_seconds_bucket[5m]))
```

### Median Latency (50th percentile)
```promql
histogram_quantile(0.5, rate(ai_request_duration_seconds_bucket[5m]))
```

### Request Rate (requests per second)
```promql
rate(ai_requests_total[5m])
```

### Error Rate
```promql
rate(ai_errors_total[5m]) / rate(ai_requests_total[5m])
```