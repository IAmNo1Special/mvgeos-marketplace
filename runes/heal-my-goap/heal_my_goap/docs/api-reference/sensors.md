---
title: SystemSensors
description: API reference for SystemSensors — 28+ live OS metrics collector.
---

# `heal_my_goap.sensors`

!!! abstract "At a Glance"
    `SystemSensors` provides 28+ real-time OS metrics (RAM, CPU, disk, network, battery, processes) via a single `read_state()` call or individual metric methods.

## Import

```python
from heal_my_goap import SystemSensors
```

---

## Class Definition

### `SystemSensors`

```python
class SystemSensors:
    def read_state(self) -> dict[str, Any]:
        """Returns a dictionary snapshot of all 28+ OS metrics."""
```

---

## Metrics Methods

| Method | Return Type | Description |
| :--- | :--- | :--- |
| `ram_usage()` | `float` | RAM usage percentage (0-100) |
| `cpu_usage()` | `float` | CPU utilization percentage |
| `disk_usage()` | `float` | Root disk partition usage percentage |
| `temp_files_count()` | `int` | Count of files in temporary directory |
| `running_processes()` | `int` | Total active process count |
| `uptime_minutes()` | `float` | System uptime in minutes |
| `network_connected()` | `bool` | True if non-loopback active interface exists |
| `battery_percent()` | `float \| None` | Battery percentage or None if unavailable |
| `battery_power_plugged()` | `bool \| None` | Charging status or None if unavailable |
| `cpu_temperature()` | `float \| None` | CPU core temperature (Celsius) or None |
| `swap_usage()` | `float` | Swap usage percentage |
| `network_bytes_sent()` | `int` | Outbound network byte counter |
| `network_bytes_recv()` | `int` | Inbound network byte counter |
| `process_memory_rss()` | `int` | Current Python process RSS memory bytes |
| `top_process_cpu_pct()` | `float` | CPU % of top consuming process |
| `disk_partitions_count()` | `int` | Active disk partition count |
| `net_connections_count()` | `int` | Active network connection socket count |
| `load_avg_1m()` | `float` | 1-minute load average |
| `load_avg_5m()` | `float` | 5-minute load average |
| `load_avg_15m()` | `float` | 15-minute load average |
| `disk_read_bytes()` | `int` | Disk read bytes counter |
| `disk_write_bytes()` | `int` | Disk write bytes counter |
| `disk_read_count()` | `int` | Disk read operations count |
| `disk_write_count()` | `int` | Disk write operations count |
| `network_packets_sent()` | `int` | Outbound network packet counter |
| `network_packets_recv()` | `int` | Inbound network packet counter |
| `context_switches()` | `int` | CPU context switches count |
| `interrupts()` | `int` | CPU interrupts count |

---

## Usage Example

```python
from heal_my_goap import SystemSensors, world_state_from_sensors

sensors = SystemSensors()

# Get all metrics at once
full_state = sensors.read_state()

# Or get individual metrics
ram_pct = sensors.ram_usage()
cpu_pct = sensors.cpu_usage()
battery = sensors.battery_percent()

# Convert directly to WorldState for GOAP
state = world_state_from_sensors(sensors)
```

---

## Related Pages

- [API Reference: GoapEngine](engine.md)
- [API Reference: Models & Helpers](models.md)
- [User Guide: Delta Observer](../user-guide/delta-observer.md)
- [Example: OS System Monitor](../examples/system-monitor.md)