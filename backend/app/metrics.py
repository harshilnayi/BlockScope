"""BlockScope Prometheus metrics definitions."""

import time

from prometheus_client import Counter, Gauge, Histogram

START_TIME = time.time()


# Total requests
REQUEST_COUNT = Counter(
    "blockscope_requests_total",
    "Total API requests",
    ["method", "endpoint", "status"],
)

ACTIVE_USERS = Gauge(
    "blockscope_active_users",
    "Number of active authenticated users",
)

# Response time
REQUEST_LATENCY = Histogram(
    "blockscope_request_latency_seconds",
    "Request latency",
    ["endpoint"],
)

# Active requests (in-flight)
ACTIVE_REQUESTS = Gauge(
    "blockscope_active_requests",
    "Active requests currently being processed",
)

# Cache metrics
CACHE_HITS = Counter(
    "blockscope_cache_hits_total",
    "Total cache hits",
    ["cache_type"],
)

CACHE_MISSES = Counter(
    "blockscope_cache_misses_total",
    "Total cache misses",
    ["cache_type"],
)

APP_UPTIME = Gauge(
      "app_uptime_seconds",
      "Application uptime in seconds",
  )

# Renamed: was ACTIVE_USERS, now correctly reflects authenticated requests
active_authenticated_requests = Gauge(
    "blockscope_active_authenticated_requests",
    "Currently active authenticated (API-key bearing) requests",
)
