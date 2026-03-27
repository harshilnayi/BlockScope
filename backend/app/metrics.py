from prometheus_client import Counter, Histogram, Gauge
import time

# total requests
REQUEST_COUNT = Counter(
    "blockscope_requests_total",
    "Total API requests",
    ["method", "endpoint", "status"]
)

# response time
REQUEST_LATENCY = Histogram(
    "blockscope_request_latency_seconds",
    "Request latency",
    ["endpoint"]
)

# active requests
ACTIVE_REQUESTS = Gauge(
    "blockscope_active_requests",
    "Active requests"
)

# uptime
START_TIME = time.time()