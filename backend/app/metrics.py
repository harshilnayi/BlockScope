from prometheus_client import Counter, Histogram, Gauge
import time

REQUEST_COUNT = Counter(
    "blockscope_requests_total",
    "Total API requests",
    ["method", "endpoint", "status"]
)

REQUEST_LATENCY = Histogram(
    "blockscope_request_latency_seconds",
    "Request latency",
    ["endpoint"]
)

ACTIVE_REQUESTS = Gauge(
    "blockscope_active_requests",
    "Active requests"
)

START_TIME = time.time()