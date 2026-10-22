from __future__ import annotations

from prometheus_client import Counter, Histogram

REQUEST_COUNT = Counter(
    "zooffer_http_requests_total", "HTTP requests", ["method", "path_template", "status"]
)
REQUEST_LATENCY = Histogram(
    "zooffer_http_request_duration_seconds", "Request latency", ["method", "path_template"]
)
SWIPES = Counter("zooffer_swipes_total", "Swipes", ["action", "source"])
MATCHES = Counter("zooffer_matches_total", "Mutual matches created")
QUOTA_REJECTIONS = Counter("zooffer_quota_rejections_total", "Quota rejections")
AUTH_FAILURES = Counter("zooffer_auth_failures_total", "Authentication failures", ["reason"])
