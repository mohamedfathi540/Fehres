from google.protobuf.internal.well_known_types import Duration
from prometheus_client import Counter, Histogram, generate_latest , CONTENT_TYPE_LATEST
from fastapi import Request, Response,FastAPI
from starlette.middleware.base import BaseHTTPMiddleware
import time

#Define metrics

REQUEST_COUNT = Counter(
    'http_request_count',
    'Total HTTP request count',
    ['method', 'endpoint', 'status_code']
)

REQUEST_LATENCY = Histogram(
    'http_request_latency',
    'HTTP request latency',
    ['method', 'endpoint']
)


#Middleware

class PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request,call_next) -> Response:

        #Record request start time
        request_start_time = time.time()
        response = await call_next(request)
        end_point = request.url.path
        #Update metrics
        REQUEST_COUNT.labels(method= request.method, endpoint= end_point, status_code= response.status_code).inc()
        REQUEST_LATENCY.labels(method= request.method, endpoint= end_point).observe(Duration)
        
        return response

def setup_metrics(app: FastAPI):
    """
    Setup prometheus metrics middleware and endpoint
    """
    #Add Prometheus middleware
    app.add_middleware(PrometheusMiddleware)
    #Add metrics endpoint
    @app.get('/kfgndfkk4464_fubfd555',include_in_schema=False) 
    def metrics():
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)