"""System sensors for real-world GOAP state collection.

Provides ``SystemSensors`` which reads live OS-level metrics via
``psutil`` and ``os`` and returns them as a flat dict suitable for
``WorldState`` construction in the GOAP planning pipeline.
"""

import os
import platform
import time
from typing import Any, cast

import psutil

__all__ = ["SystemSensors"]


class SystemSensors:
    """Collects real-time system metrics for GOAP WorldState population.

    Attributes:
        hostname: The machine's network name.
        os_name: The operating system identifier.
    """

    def __init__(self) -> None:
        """Initializes SystemSensors and captures static host info."""
        self.hostname: str = platform.node()
        self.os_name: str = platform.system()

    def read_state(self) -> dict[str, Any]:
        """Captures a full snapshot of system metrics as a flat dict.

        Returns:
            A dictionary of predicate names to current values,
            ready for direct construction of a ``WorldState``.
        """
        return {
            "ram_usage_pct": self.ram_usage(),
            "cpu_usage_pct": self.cpu_usage(),
            "disk_usage_pct": self.disk_usage(),
            "cwd": self.current_working_directory(),
            "temp_files_count": self.temp_files_count(),
            "running_processes": self.running_processes(),
            "uptime_minutes": self.uptime_minutes(),
            "network_connected": self.network_connected(),
            "battery_pct": self.battery_percent(),
            "battery_plugged": self.battery_power_plugged(),
            "cpu_temp_celsius": self.cpu_temperature(),
            "swap_usage_pct": self.swap_usage(),
            "network_bytes_sent": self.network_bytes_sent(),
            "network_bytes_recv": self.network_bytes_recv(),
            "cpu_count": self.cpu_count(),
            "cpu_freq_mhz": self.cpu_freq(),
            "disk_io_read_bytes": self.disk_io_read_bytes(),
            "disk_io_write_bytes": self.disk_io_write_bytes(),
            "num_logged_in_users": self.num_logged_in_users(),
            "load_avg_1m": self.load_avg_1m(),
            "available_memory": self.available_memory(),
            "virtual_memory_total": self.virtual_memory_total(),
            "swap_total": self.swap_total(),
            "swap_free": self.swap_free(),
            "process_memory_rss": self.process_memory_rss(),
            "top_process_cpu_pct": self.top_process_cpu_pct(),
            "disk_partitions_count": self.disk_partitions_count(),
            "net_connections_count": self.net_connections_count(),
            "hostname": self.hostname,
            "os_name": self.os_name,
        }

    def ram_usage(self) -> float:
        """Returns current RAM usage as a percentage (0-100).

        Returns:
            Float percentage of total physical memory in use.
        """
        return cast(float, psutil.virtual_memory().percent)

    def cpu_usage(self) -> float:
        """Returns current CPU usage as a percentage (0-100).

        Returns:
            Float percentage of CPU utilization over a 0.1s interval.
        """
        return cast(float, psutil.cpu_percent(interval=0.1))

    def disk_usage(self) -> float:
        """Returns current disk usage of the root partition as a percentage.

        Returns:
            Float percentage of total disk space in use.
        """
        return cast(float, psutil.disk_usage("/").percent)

    def current_working_directory(self) -> str:
        """Returns the process current working directory.

        Returns:
            Absolute path string of the CWD.
        """
        return os.getcwd()

    def temp_files_count(self) -> int:
        """Counts temporary files in the system temp directory.

        Returns:
            Integer count of files in ``tempfile.gettempdir()``.
        """
        tmp_dir = os.path.join(
            os.path.expanduser("~"), "AppData", "Local", "Temp"
        )
        if not os.path.isdir(tmp_dir):
            tmp_dir = os.getenv("TMPDIR") or "/tmp"
        try:
            return len(os.listdir(tmp_dir))
        except OSError:
            return 0

    def running_processes(self) -> int:
        """Returns the number of currently running processes.

        Returns:
            Integer count of active process IDs.
        """
        return len(psutil.pids())

    def uptime_minutes(self) -> float:
        """Returns system uptime in minutes.

        Returns:
            Float number of minutes since last boot.
        """
        boot_time = cast(float, psutil.boot_time())
        return (time.time() - boot_time) / 60.0

    def network_connected(self) -> bool:
        """Checks whether the system has an active network connection.

        Returns:
            True if any network interface has a non-loopback address
            and is connected, False otherwise.
        """
        addrs = psutil.net_if_addrs()
        stats = psutil.net_if_stats()
        for iface, addr_list in addrs.items():
            if iface == "lo":
                continue
            for addr in addr_list:
                if addr.family.name in ("AF_INET", "AF_INET6"):
                    if iface in stats and stats[iface].isup:
                        return True
        return False

    def battery_percent(self) -> float | None:
        """Returns current battery charge as a percentage.

        Returns:
            Float percentage (0-100) if a battery is present,
            None if no battery is detected.
        """
        battery = psutil.sensors_battery()
        if battery is None:
            return None
        return cast(float, battery.percent)

    def battery_power_plugged(self) -> bool | None:
        """Returns whether the system is currently charging.

        Returns:
            True if power is plugged in, False if on battery,
            None if no battery is detected.
        """
        battery = psutil.sensors_battery()
        if battery is None:
            return None
        return cast(bool, battery.power_plugged)

    def cpu_temperature(self) -> float | None:
        """Returns CPU temperature in Celsius if available.

        Returns:
            Float temperature in degrees Celsius, or None if
            the sensor is unavailable or unsupported on this
            platform.
        """
        try:
            temps = psutil.sensors_temperatures()
        except AttributeError:
            return None
        for name, entries in temps.items():
            for entry in entries:
                if "core" in name.lower() or "cpu" in name.lower():
                    return cast(float, entry.current)
        return None

    def swap_usage(self) -> float:
        """Returns swap memory usage as a percentage (0-100).

        Returns:
            Float percentage of total swap space in use.
        """
        return cast(float, psutil.swap_memory().percent)

    def network_bytes_sent(self) -> int:
        """Returns total bytes sent over all network interfaces.

        Returns:
            Integer byte count of outbound network traffic.
        """
        return cast(int, psutil.net_io_counters().bytes_sent)

    def network_bytes_recv(self) -> int:
        """Returns total bytes received over all network interfaces.

        Returns:
            Integer byte count of inbound network traffic.
        """
        return cast(int, psutil.net_io_counters().bytes_recv)

    def cpu_count(self) -> int:
        """Returns the number of logical CPU cores.

        Returns:
            Integer count of logical CPUs available to the process.
        """
        return cast(int, psutil.cpu_count(logical=True) or 0)

    def cpu_freq(self) -> float | None:
        """Returns current CPU frequency in MHz.

        Returns:
            Float frequency in MHz, or None if the sensor
            is unavailable (e.g., on some virtualized environments).
        """
        freq = psutil.cpu_freq()
        if freq is None:
            return None
        return cast(float, freq.current)

    def disk_io_read_bytes(self) -> int:
        """Returns total bytes read from disk across all partitions.

        Returns:
            Integer byte count of disk read operations.
        """
        return cast(int, psutil.disk_io_counters().read_bytes)

    def disk_io_write_bytes(self) -> int:
        """Returns total bytes written to disk across all partitions.

        Returns:
            Integer byte count of disk write operations.
        """
        return cast(int, psutil.disk_io_counters().write_bytes)

    def num_logged_in_users(self) -> int:
        """Returns the number of users currently logged in.

        Returns:
            Integer count of logged-in user sessions.
        """
        return len(psutil.users())

    def load_avg_1m(self) -> float | None:
        """Returns the 1-minute load average if available.

        Returns:
            Float load average, or None on platforms where
            load averages are not supported (e.g., Windows).
        """
        try:
            return cast(float, psutil.getloadavg()[0])
        except NotImplementedError:
            return None

    def available_memory(self) -> int:
        """Returns available physical memory in bytes.

        Returns:
            Integer byte count of freely available RAM.
        """
        return cast(int, psutil.virtual_memory().available)

    def virtual_memory_total(self) -> int:
        """Returns total physical memory in bytes.

        Returns:
            Integer byte count of total installed RAM.
        """
        return cast(int, psutil.virtual_memory().total)

    def swap_total(self) -> int:
        """Returns total swap space in bytes.

        Returns:
            Integer byte count of total swap partition/file size.
        """
        return cast(int, psutil.swap_memory().total)

    def swap_free(self) -> int:
        """Returns free swap space in bytes.

        Returns:
            Integer byte count of free swap space.
        """
        return cast(int, psutil.swap_memory().free)

    def environment_variable(self, name: str) -> str | None:
        """Reads a single environment variable by name.

        Args:
            name: The environment variable key to look up.

        Returns:
            The variable value as a string, or None if unset.
        """
        return os.environ.get(name)

    def environment_variables(self, names: list[str]) -> dict[str, str | None]:
        """Reads multiple environment variables at once.

        Args:
            names: List of environment variable keys to retrieve.

        Returns:
            A dict mapping each requested name to its value (or None).
        """
        return {name: self.environment_variable(name) for name in names}

    def process_memory_rss(self) -> int:
        """Returns Resident Set Size (RSS) memory of current process in bytes.

        Returns:
            Integer byte count of RSS memory used by this Python process.
        """
        return cast(int, psutil.Process().memory_info().rss)

    def top_process_cpu_pct(self) -> float:
        """Returns CPU usage percentage of current process.

        Returns:
            Float CPU percentage of current process.
        """
        return cast(float, psutil.Process().cpu_percent(interval=0.0))

    def disk_partitions_count(self) -> int:
        """Returns total count of mounted disk partitions.

        Returns:
            Integer count of active physical/virtual disk partitions.
        """
        return len(psutil.disk_partitions(all=False))

    def net_connections_count(self) -> int:
        """Returns count of active network connections.

        Returns:
            Integer count of active socket connections, or 0 if restricted.
        """
        try:
            return len(psutil.net_connections())
        except (psutil.AccessDenied, PermissionError):
            return 0
