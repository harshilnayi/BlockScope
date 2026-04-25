# 📊 BlockScope — Metrics & Monitoring Guide

> **Architecture:** Backend (`/metrics`) → **Prometheus** (scrape & store) → **Grafana** (visualize)

This guide explains how to set up **production-grade** metrics visualization for BlockScope using the industry-standard Prometheus + Grafana stack.

---

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Quick Start (Docker)](#quick-start-docker)
- [Manual Setup](#manual-setup)
  - [1. Prometheus](#1-prometheus)
  - [2. Grafana](#2-grafana)
- [Available Metrics](#available-metrics)
- [Dashboard Panels](#dashboard-panels)
- [Grafana Queries Reference](#grafana-queries-reference)
- [Verifying the Setup](#verifying-the-setup)
- [Troubleshooting](#troubleshooting)

---

## Overview

BlockScope exposes a **Prometheus-compatible** metrics endpoint:

```
GET http://localhost:8000/metrics
```

This returns metrics in the OpenMetrics/Prometheus text format, ready to be scraped.

```
┌──────────────┐       scrape        ┌──────────────┐       query        ┌──────────────┐
│  BlockScope  │ ──────────────────► │  Prometheus  │ ──────────────────► │   Grafana    │
│  :8000       │   /metrics (5s)     │  :9090       │   PromQL           │  :3001       │
└──────────────┘                     └──────────────┘                     └──────────────┘
```

---

## Prerequisites

| Tool              | Required For       | Install                                      |
| ----------------- | ------------------ | -------------------------------------------- |
| Docker & Compose  | Automated setup    | [docs.docker.com](https://docs.docker.com)   |
| BlockScope API    | Metrics source     | See main [README](../README.md)              |

Make sure the BlockScope backend is running on **port 8000** before starting the monitoring stack.

---

## Quick Start (Docker)

The fastest way to get everything running — **one command**:

```bash
# 1. Start the BlockScope backend (if not already running)
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 2. In a new terminal, start the monitoring stack
cd /path/to/isok
docker compose -f docker-compose.monitoring.yml up -d
```

That's it. Open your browser:

| Service    | URL                        | Credentials       |
| ---------- | -------------------------- | ------------------ |
| Prometheus | http://localhost:9090       | —                  |
| Grafana    | http://localhost:3001       | `admin` / `admin`  |

The **BlockScope — API Monitoring** dashboard is auto-provisioned and ready to view.

### Stop the stack

```bash
docker compose -f docker-compose.monitoring.yml down
```

### Reset all data

```bash
docker compose -f docker-compose.monitoring.yml down -v
```

---

## Manual Setup

If you prefer to install Prometheus and Grafana without Docker:

### 1. Prometheus

#### Install

```bash
# macOS
brew install prometheus

# Linux (download binary)
wget https://github.com/prometheus/prometheus/releases/download/v2.53.0/prometheus-2.53.0.linux-amd64.tar.gz
tar xvfz prometheus-*.tar.gz
cd prometheus-*
```

#### Configure

Use the provided configuration at [`monitoring/prometheus.yml`](../monitoring/prometheus.yml):

```yaml
global:
  scrape_interval: 5s

scrape_configs:
  - job_name: "blockscope"
    metrics_path: "/metrics"
    static_configs:
      - targets: ["localhost:8000"]
        labels:
          environment: "development"
          service: "blockscope-api"
```

#### Run

```bash
prometheus --config.file=monitoring/prometheus.yml
```

#### Verify

- Open http://localhost:9090
- Navigate to **Status → Targets**
- Confirm the `blockscope` target shows **UP**

---

### 2. Grafana

#### Install

```bash
# macOS
brew install grafana

# Linux (APT)
sudo apt-get install -y adduser libfontconfig1
wget https://dl.grafana.com/oss/release/grafana_11.1.0_amd64.deb
sudo dpkg -i grafana_11.1.0_amd64.deb

# Start
sudo systemctl start grafana-server
```

#### Add Prometheus Data Source

1. Open **http://localhost:3000** (default port for manual install)
2. Log in with `admin` / `admin`
3. Go to **⚙️ Connections → Data Sources → Add data source**
4. Select **Prometheus**
5. Set the URL to:
   ```
   http://localhost:9090
   ```
6. Click **Save & Test** — should show ✅ *"Successfully queried the Prometheus API"*

#### Import the Dashboard

1. Go to **Dashboards → Import**
2. Click **Upload JSON file**
3. Select [`monitoring/grafana/dashboards/blockscope.json`](../monitoring/grafana/dashboards/blockscope.json)
4. Select your **Prometheus** data source from the dropdown
5. Click **Import**

---

## Available Metrics

The `/metrics` endpoint exposes the following BlockScope-specific metrics:

| Metric                                    | Type      | Labels                       | Description                          |
| ----------------------------------------- | --------- | ---------------------------- | ------------------------------------ |
| `blockscope_requests_total`               | Counter   | `method`, `endpoint`, `status` | Total API requests                   |
| `blockscope_request_latency_seconds`      | Histogram | `endpoint`                   | Request latency distribution         |
| `blockscope_active_requests`              | Gauge     | —                            | Currently in-flight requests         |
| `blockscope_cache_hits_total`             | Counter   | `cache_type`                 | Total cache hits                     |
| `blockscope_cache_misses_total`           | Counter   | `cache_type`                 | Total cache misses                   |
| `blockscope_active_users`                 | Gauge     | —                            | Currently active authenticated users |
| `blockscope_uptime_seconds`              | Gauge     | —                            | Application uptime in seconds        |

---

## Dashboard Panels

The pre-built Grafana dashboard includes the following panels:

### Overview Row (Stat Panels)

| Panel            | Query                                                                                       |
| ---------------- | ------------------------------------------------------------------------------------------- |
| Uptime           | `blockscope_uptime_seconds`                                                                 |
| Active Users     | `blockscope_active_users`                                                                   |
| Request Rate     | `sum(rate(blockscope_requests_total[1m]))`                                                  |
| P95 Latency      | `histogram_quantile(0.95, sum(rate(blockscope_request_latency_seconds_bucket[5m])) by (le))` |
| Cache Hit Rate   | `sum(rate(blockscope_cache_hits_total[1m])) / (sum(rate(…hits…)) + sum(rate(…misses…)))`     |
| Error Rate       | `sum(rate(blockscope_requests_total{status=~"5.."}[1m]))`                                   |

### Request Metrics Row

- **Request Rate by Endpoint** — timeseries, broken down by `endpoint` label
- **Request Rate by Status Code** — stacked bar chart by `status`
- **Error Rate (5xx vs 4xx)** — timeseries comparing server and client errors
- **Active Requests** — in-flight request gauge

### Latency Row

- **Response Time Percentiles** — p50 / p90 / p95 / p99 over time
- **Average Latency by Endpoint** — per-endpoint mean response time

### Cache Performance Row

- **Cache Hit Rate** — hit ratio as a percentage over time
- **Cache Hits vs Misses** — side-by-side rate comparison per `cache_type`

---

## Grafana Queries Reference

Use these PromQL queries directly in Grafana's **Explore** tab or in custom panels:

### Request Rate (overall)
```promql
sum(rate(blockscope_requests_total[1m]))
```

### Request Rate by Method
```promql
sum(rate(blockscope_requests_total[1m])) by (method)
```

### Error Rate (5xx only)
```promql
sum(rate(blockscope_requests_total{status=~"5.."}[1m]))
```

### Error Percentage
```promql
sum(rate(blockscope_requests_total{status=~"5.."}[1m]))
/
sum(rate(blockscope_requests_total[1m])) * 100
```

### Response Time — P95
```promql
histogram_quantile(0.95, sum(rate(blockscope_request_latency_seconds_bucket[5m])) by (le))
```

### Response Time — P99
```promql
histogram_quantile(0.99, sum(rate(blockscope_request_latency_seconds_bucket[5m])) by (le))
```

### Average Response Time
```promql
rate(blockscope_request_latency_seconds_sum[5m])
/
rate(blockscope_request_latency_seconds_count[5m])
```

### Cache Hit Rate
```promql
sum(rate(blockscope_cache_hits_total[1m]))
/
(sum(rate(blockscope_cache_hits_total[1m])) + sum(rate(blockscope_cache_misses_total[1m])))
```

### Active Users
```promql
blockscope_active_users
```

### Uptime
```promql
blockscope_uptime_seconds
```

---

## Verifying the Setup

### 1. Check the `/metrics` endpoint

```bash
curl -s http://localhost:8000/metrics | head -20
```

Expected output (Prometheus text format):
```
# HELP blockscope_requests_total Total API requests
# TYPE blockscope_requests_total counter
blockscope_requests_total{method="GET",endpoint="/",status="200"} 5.0
...
```

### 2. Check Prometheus is scraping

Open http://localhost:9090/targets — the `blockscope` job should show:

| Endpoint               | State | Last Scrape |
| ---------------------- | ----- | ----------- |
| `localhost:8000`       | **UP** | 3s ago      |

### 3. Check Grafana shows data

1. Open http://localhost:3001
2. Navigate to **Dashboards → BlockScope → BlockScope — API Monitoring**
3. Generate some traffic:
   ```bash
   # Quick load test
   for i in $(seq 1 50); do curl -s http://localhost:8000/ > /dev/null; done
   ```
4. Panels should populate within 5-10 seconds

---

## Troubleshooting

### Prometheus shows target as DOWN

| Cause | Fix |
| ----- | --- |
| Backend not running | Start with `uvicorn app.main:app --port 8000` |
| Wrong target address | Docker users: use `host.docker.internal:8000` in `prometheus.yml` |
| Firewall blocking | Ensure port 8000 is accessible from the Prometheus container |

### Grafana shows "No data"

| Cause | Fix |
| ----- | --- |
| Data source not configured | Add Prometheus at `http://prometheus:9090` (Docker) or `http://localhost:9090` (manual) |
| No traffic yet | Hit some endpoints to generate metrics data |
| Time range too narrow | Expand the time picker to "Last 1 hour" |

### Dashboard not auto-loading

If you see an empty Grafana with no dashboards:

```bash
# Restart Grafana to re-provision
docker compose -f docker-compose.monitoring.yml restart grafana
```

### Cannot connect between containers

Make sure Docker networking allows inter-container access. The `host.docker.internal` hostname resolves to the host machine on Docker Desktop. On Linux, the `extra_hosts` directive in `docker-compose.monitoring.yml` handles this.

---

## File Structure

```
BlockScope/
├── docker-compose.monitoring.yml     # Spin up Prometheus + Grafana
├── monitoring/
│   ├── prometheus.yml                # Prometheus scrape configuration
│   └── grafana/
│       ├── provisioning/
│       │   ├── datasources/
│       │   │   └── datasource.yml    # Auto-provision Prometheus datasource
│       │   └── dashboards/
│       │       └── dashboard.yml     # Auto-provision dashboard provider
│       └── dashboards/
│           └── blockscope.json       # Pre-built Grafana dashboard
└── backend/
    └── app/
        ├── metrics.py                # Prometheus metric definitions
        └── main.py                   # /metrics endpoint + middleware
```

---

## Next Steps

- **Alerting**: Configure Grafana alerts for error rate thresholds or increased latency
- **Production**: Use persistent volumes and external Prometheus/Grafana instances
- **Additional metrics**: Add business-specific metrics (scan results, vulnerability counts)
