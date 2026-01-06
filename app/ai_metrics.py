import time
from prometheus_client import Counter, Histogram

# AI metrics (import these from process.py)
AI_REQUEST_COUNT = Counter('ai_requests_total', 'Total AI requests', ['model', 'operation'])
AI_LATENCY = Histogram('ai_request_duration_seconds', 'AI request latency', ['model', 'operation'])
AI_TOKEN_COUNT = Counter('ai_tokens_total', 'Total AI tokens used', ['model', 'type'])
AI_ERROR_COUNT = Counter('ai_errors_total', 'Total AI errors', ['model', 'error_type'])
AI_CONFIDENCE_SCORE = Histogram('ai_confidence_score', 'AI model confidence scores', ['model', 'operation'])

def track_ai_metrics(model_name, operation):
    """Decorator to track AI model metrics"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            AI_REQUEST_COUNT.labels(model=model_name, operation=operation).inc()
            
            try:
                result = func(*args, **kwargs)
                
                # Track latency
                latency = time.time() - start_time
                AI_LATENCY.labels(model=model_name, operation=operation).observe(latency)
                
                # Track tokens if available in result
                if isinstance(result, dict):
                    if 'input_tokens' in result:
                        AI_TOKEN_COUNT.labels(model=model_name, type='input').inc(result['input_tokens'])
                    if 'output_tokens' in result:
                        AI_TOKEN_COUNT.labels(model=model_name, type='output').inc(result['output_tokens'])
                    if 'confidence' in result:
                        AI_CONFIDENCE_SCORE.labels(model=model_name, operation=operation).observe(result['confidence'])
                
                return result
                
            except Exception as e:
                AI_ERROR_COUNT.labels(model=model_name, error_type=type(e).__name__).inc()
                raise
                
        return wrapper
    return decorator