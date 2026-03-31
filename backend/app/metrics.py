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

# NEW — cache hit rate
CACHE_HITS = Counter(
    "blockscope_cache_hits_total",
    "Cache hits"
)

CACHE_MISSES = Counter(
    "blockscope_cache_misses_total",
    "Cache misses"
)

# NEW — active users
ACTIVE_USERS = Gauge(
    "blockscope_active_users",
    "Currently active users"
)

START_TIME = time.time()