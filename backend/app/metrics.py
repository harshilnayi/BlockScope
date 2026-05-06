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

# cache metrics
CACHE_HITS = Counter(
    "blockscope_cache_hits_total",
    "Total cache hits",
    ["cache_type"]
)

CACHE_MISSES = Counter(
    "blockscope_cache_misses_total",
    "Total cache misses",
    ["cache_type"]
)

# active users (authenticated sessions)
ACTIVE_USERS = Gauge(
    "blockscope_active_users",
    "Currently active authenticated users"
)

# uptime
START_TIME = time.time()

APP_UPTIME = Gauge(
    "blockscope_uptime_seconds",
    "Application uptime in seconds"
)
