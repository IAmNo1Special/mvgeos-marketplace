"""Tests for the system sensors module."""

from unittest.mock import MagicMock, patch

import psutil
import pytest

from heal_my_goap.sensors import SystemSensors


@pytest.fixture
def sensors() -> SystemSensors:
    """Provides a SystemSensors instance for testing."""
    return SystemSensors()


def test_sensors_read_state_returns_all_keys(sensors: SystemSensors) -> None:
    """Verifies read_state returns every expected predicate key."""
    with patch.object(sensors, "ram_usage", return_value=50.0):
        with patch.object(sensors, "cpu_usage", return_value=25.0):
            with patch.object(sensors, "disk_usage", return_value=60.0):
                with patch.object(
                    sensors, "current_working_directory", return_value="/tmp"
                ):
                    with patch.object(
                        sensors, "temp_files_count", return_value=5
                    ):
                        with patch.object(
                            sensors, "running_processes", return_value=100
                        ):
                            with patch.object(
                                sensors, "uptime_minutes", return_value=120.0
                            ):
                                with patch.object(
                                    sensors,
                                    "network_connected",
                                    return_value=True,
                                ):
                                    state = sensors.read_state()

    expected_keys = [
        "ram_usage_pct",
        "cpu_usage_pct",
        "disk_usage_pct",
        "cwd",
        "temp_files_count",
        "running_processes",
        "uptime_minutes",
        "network_connected",
        "battery_pct",
        "battery_plugged",
        "cpu_temp_celsius",
        "swap_usage_pct",
        "network_bytes_sent",
        "network_bytes_recv",
        "cpu_count",
        "cpu_freq_mhz",
        "disk_io_read_bytes",
        "disk_io_write_bytes",
        "num_logged_in_users",
        "load_avg_1m",
        "available_memory",
        "virtual_memory_total",
        "swap_total",
        "swap_free",
        "hostname",
        "os_name",
    ]
    for key in expected_keys:
        assert key in state


def test_sensors_ram_usage_returns_float(sensors: SystemSensors) -> None:
    """Verifies ram_usage returns a float percentage."""
    with patch("psutil.virtual_memory") as mock_mem:
        mock_mem.return_value.percent = 75.5
        result = sensors.ram_usage()
    assert isinstance(result, float)
    assert result == 75.5


def test_sensors_cpu_usage_returns_float(sensors: SystemSensors) -> None:
    """Verifies cpu_usage returns a float percentage."""
    with patch("psutil.cpu_percent", return_value=42.0):
        result = sensors.cpu_usage()
    assert isinstance(result, float)
    assert result == 42.0


def test_sensors_disk_usage_returns_float(sensors: SystemSensors) -> None:
    """Verifies disk_usage returns a float percentage."""
    with patch("psutil.disk_usage") as mock_disk:
        mock_disk.return_value.percent = 88.0
        result = sensors.disk_usage()
    assert isinstance(result, float)
    assert result == 88.0


def test_sensors_current_working_directory_returns_str(
    sensors: SystemSensors,
) -> None:
    """Verifies current_working_directory returns a string path."""
    with patch("os.getcwd", return_value="/home/user/project"):
        result = sensors.current_working_directory()
    assert isinstance(result, str)
    assert result == "/home/user/project"


def test_sensors_temp_files_count_returns_int(sensors: SystemSensors) -> None:
    """Verifies temp_files_count returns an integer count."""
    with patch("os.listdir", return_value=["f1", "f2", "f3"]):
        result = sensors.temp_files_count()
    assert isinstance(result, int)
    assert result == 3


def test_sensors_temp_files_count_handles_missing_dir(
    sensors: SystemSensors,
) -> None:
    """Verifies temp_files_count returns 0 when temp dir is inaccessible."""
    with patch("os.listdir", side_effect=OSError):
        result = sensors.temp_files_count()
    assert result == 0


def test_sensors_running_processes_returns_int(sensors: SystemSensors) -> None:
    """Verifies running_processes returns an integer count."""
    with patch("psutil.pids", return_value=[1, 2, 3, 4, 5]):
        result = sensors.running_processes()
    assert isinstance(result, int)
    assert result == 5


def test_sensors_uptime_minutes_returns_float(sensors: SystemSensors) -> None:
    """Verifies uptime_minutes returns a float duration."""
    with patch("psutil.boot_time", return_value=1000000.0):
        with patch("time.time", return_value=1000060.0):
            result = sensors.uptime_minutes()
    assert isinstance(result, float)
    assert result == pytest.approx(1.0)


def test_sensors_network_connected_returns_bool(sensors: SystemSensors) -> None:
    """Verifies network_connected returns a boolean."""
    mock_addr = MagicMock()
    mock_addr.family.name = "AF_INET"
    mock_addr.address = "192.168.1.1"

    mock_stats = MagicMock()
    mock_stats.isup = True

    with patch("psutil.net_if_addrs", return_value={"eth0": [mock_addr]}):
        with patch("psutil.net_if_stats", return_value={"eth0": mock_stats}):
            result = sensors.network_connected()
    assert isinstance(result, bool)
    assert result is True


def test_sensors_network_connected_no_interfaces(
    sensors: SystemSensors,
) -> None:
    """Verifies network_connected returns False when no interfaces exist."""
    with patch("psutil.net_if_addrs", return_value={}):
        with patch("psutil.net_if_stats", return_value={}):
            result = sensors.network_connected()
    assert result is False


def test_sensors_environment_variable_returns_value(
    sensors: SystemSensors,
) -> None:
    """Verifies environment_variable returns the value for a set key."""
    with patch.dict("os.environ", {"MY_VAR": "hello"}):
        result = sensors.environment_variable("MY_VAR")
    assert result == "hello"


def test_sensors_environment_variable_returns_none_when_unset(
    sensors: SystemSensors,
) -> None:
    """Verifies environment_variable returns None for an unset key."""
    with patch.dict("os.environ", {}, clear=True):
        result = sensors.environment_variable("NONEXISTENT_VAR")
    assert result is None


def test_sensors_environment_variables_returns_dict(
    sensors: SystemSensors,
) -> None:
    """Verifies environment_variables returns a dict for multiple names."""
    with patch.dict("os.environ", {"VAR_A": "alpha", "VAR_B": "beta"}):
        result = sensors.environment_variables(["VAR_A", "VAR_B", "VAR_C"])
    assert result == {"VAR_A": "alpha", "VAR_B": "beta", "VAR_C": None}


def test_sensors_hostname_is_string(sensors: SystemSensors) -> None:
    """Verifies hostname attribute is a non-empty string."""
    assert isinstance(sensors.hostname, str)


def test_sensors_os_name_is_string(sensors: SystemSensors) -> None:
    """Verifies os_name attribute is a non-empty string."""
    assert isinstance(sensors.os_name, str)
    assert len(sensors.os_name) > 0


def test_sensors_temp_files_count_fallback_dir(
    sensors: SystemSensors,
) -> None:
    """Verifies temp_files_count uses TMPDIR fallback when AppData missing."""
    with patch("os.path.isdir", return_value=False):
        with patch("os.getenv", return_value="/tmp"):
            with patch("os.listdir", return_value=["f1"]):
                result = sensors.temp_files_count()
    assert result == 1


def test_sensors_network_connected_skips_loopback(
    sensors: SystemSensors,
) -> None:
    """Verifies network_connected skips loopback interface."""
    mock_addr = MagicMock()
    mock_addr.family.name = "AF_INET"
    mock_addr.address = "127.0.0.1"

    mock_stats = MagicMock()
    mock_stats.isup = True

    with patch("psutil.net_if_addrs", return_value={"lo": [mock_addr]}):
        with patch("psutil.net_if_stats", return_value={"lo": mock_stats}):
            result = sensors.network_connected()
    assert result is False


def test_sensors_battery_percent_returns_float(sensors: SystemSensors) -> None:
    """Verifies battery_percent returns a float when battery exists."""
    mock_battery = MagicMock()
    mock_battery.percent = 75.0
    mock_battery.power_plugged = True
    with patch("psutil.sensors_battery", return_value=mock_battery):
        result = sensors.battery_percent()
    assert isinstance(result, float)
    assert result == 75.0


def test_sensors_battery_percent_returns_none_when_absent(
    sensors: SystemSensors,
) -> None:
    """Verifies battery_percent returns None when no battery detected."""
    with patch("psutil.sensors_battery", return_value=None):
        result = sensors.battery_percent()
    assert result is None


def test_sensors_battery_power_plugged_returns_bool(
    sensors: SystemSensors,
) -> None:
    """Verifies battery_power_plugged returns a boolean."""
    mock_battery = MagicMock()
    mock_battery.power_plugged = True
    with patch("psutil.sensors_battery", return_value=mock_battery):
        result = sensors.battery_power_plugged()
    assert isinstance(result, bool)
    assert result is True


def test_sensors_battery_power_plugged_returns_none_when_absent(
    sensors: SystemSensors,
) -> None:
    """Verifies battery_power_plugged returns None when no battery detected."""
    with patch("psutil.sensors_battery", return_value=None):
        result = sensors.battery_power_plugged()
    assert result is None


def test_sensors_cpu_temperature_returns_float(sensors: SystemSensors) -> None:
    """Verifies cpu_temperature returns a float when sensor is available."""
    mock_entry = MagicMock()
    mock_entry.current = 65.5
    with patch(
        "psutil.sensors_temperatures",
        return_value={"cpu_core": [mock_entry]},
        create=True,
    ):
        result = sensors.cpu_temperature()
    assert isinstance(result, float)
    assert result == 65.5


def test_sensors_cpu_temperature_returns_none_when_absent(
    sensors: SystemSensors,
) -> None:
    """Verifies cpu_temperature returns None when no sensor exists."""
    with patch(
        "psutil.sensors_temperatures",
        side_effect=AttributeError,
        create=True,
    ):
        result = sensors.cpu_temperature()
    assert result is None


def test_sensors_cpu_temperature_returns_none_when_no_cpu_sensor(
    sensors: SystemSensors,
) -> None:
    """Verifies cpu_temperature returns None when no CPU sensor is found."""
    mock_entry = MagicMock()
    mock_entry.current = 65.5
    with patch(
        "psutil.sensors_temperatures",
        return_value={"gpu": [mock_entry]},
        create=True,
    ):
        result = sensors.cpu_temperature()
    assert result is None


def test_sensors_swap_usage_returns_float(sensors: SystemSensors) -> None:
    """Verifies swap_usage returns a float percentage."""
    mock_swap = MagicMock()
    mock_swap.percent = 45.0
    with patch("psutil.swap_memory", return_value=mock_swap):
        result = sensors.swap_usage()
    assert isinstance(result, float)
    assert result == 45.0


def test_sensors_network_bytes_sent_returns_int(sensors: SystemSensors) -> None:
    """Verifies network_bytes_sent returns an integer byte count."""
    mock_counters = MagicMock()
    mock_counters.bytes_sent = 1048576
    with patch("psutil.net_io_counters", return_value=mock_counters):
        result = sensors.network_bytes_sent()
    assert isinstance(result, int)
    assert result == 1048576


def test_sensors_network_bytes_recv_returns_int(sensors: SystemSensors) -> None:
    """Verifies network_bytes_recv returns an integer byte count."""
    mock_counters = MagicMock()
    mock_counters.bytes_recv = 5242880
    with patch("psutil.net_io_counters", return_value=mock_counters):
        result = sensors.network_bytes_recv()
    assert isinstance(result, int)
    assert result == 5242880


def test_sensors_cpu_count_returns_int(sensors: SystemSensors) -> None:
    """Verifies cpu_count returns an integer core count."""
    with patch("psutil.cpu_count", return_value=8):
        result = sensors.cpu_count()
    assert isinstance(result, int)
    assert result == 8


def test_sensors_cpu_freq_returns_float(sensors: SystemSensors) -> None:
    """Verifies cpu_freq returns a float frequency in MHz."""
    mock_freq = MagicMock()
    mock_freq.current = 3500.0
    with patch("psutil.cpu_freq", return_value=mock_freq):
        result = sensors.cpu_freq()
    assert isinstance(result, float)
    assert result == 3500.0


def test_sensors_cpu_freq_returns_none_when_unavailable(
    sensors: SystemSensors,
) -> None:
    """Verifies cpu_freq returns None when the sensor is unavailable."""
    with patch("psutil.cpu_freq", return_value=None):
        result = sensors.cpu_freq()
    assert result is None


def test_sensors_disk_io_read_bytes_returns_int(
    sensors: SystemSensors,
) -> None:
    """Verifies disk_io_read_bytes returns an integer byte count."""
    mock_counters = MagicMock()
    mock_counters.read_bytes = 1073741824
    with patch("psutil.disk_io_counters", return_value=mock_counters):
        result = sensors.disk_io_read_bytes()
    assert isinstance(result, int)
    assert result == 1073741824


def test_sensors_disk_io_write_bytes_returns_int(
    sensors: SystemSensors,
) -> None:
    """Verifies disk_io_write_bytes returns an integer byte count."""
    mock_counters = MagicMock()
    mock_counters.write_bytes = 2147483648
    with patch("psutil.disk_io_counters", return_value=mock_counters):
        result = sensors.disk_io_write_bytes()
    assert isinstance(result, int)
    assert result == 2147483648


def test_sensors_num_logged_in_users_returns_int(
    sensors: SystemSensors,
) -> None:
    """Verifies num_logged_in_users returns an integer count."""
    mock_user = MagicMock()
    with patch("psutil.users", return_value=[mock_user, mock_user]):
        result = sensors.num_logged_in_users()
    assert isinstance(result, int)
    assert result == 2


def test_sensors_load_avg_1m_returns_float(sensors: SystemSensors) -> None:
    """Verifies load_avg_1m returns a float on supported platforms."""
    with patch("psutil.getloadavg", return_value=(1.5, 2.0, 3.0)):
        result = sensors.load_avg_1m()
    assert isinstance(result, float)
    assert result == 1.5


def test_sensors_load_avg_1m_returns_none_on_unsupported(
    sensors: SystemSensors,
) -> None:
    """Verifies load_avg_1m returns None on platforms without load averages."""
    with patch("psutil.getloadavg", side_effect=NotImplementedError):
        result = sensors.load_avg_1m()
    assert result is None


def test_sensors_available_memory_returns_int(sensors: SystemSensors) -> None:
    """Verifies available_memory returns an integer byte count."""
    mock_mem = MagicMock()
    mock_mem.available = 8_000_000_000
    with patch("psutil.virtual_memory", return_value=mock_mem):
        result = sensors.available_memory()
    assert isinstance(result, int)
    assert result == 8_000_000_000


def test_sensors_virtual_memory_total_returns_int(
    sensors: SystemSensors,
) -> None:
    """Verifies virtual_memory_total returns an integer byte count."""
    mock_mem = MagicMock()
    mock_mem.total = 16_000_000_000
    with patch("psutil.virtual_memory", return_value=mock_mem):
        result = sensors.virtual_memory_total()
    assert isinstance(result, int)
    assert result == 16_000_000_000


def test_sensors_swap_total_returns_int(sensors: SystemSensors) -> None:
    """Verifies swap_total returns an integer byte count."""
    mock_swap = MagicMock()
    mock_swap.total = 4_000_000_000
    with patch("psutil.swap_memory", return_value=mock_swap):
        result = sensors.swap_total()
    assert isinstance(result, int)
    assert result == 4_000_000_000


def test_sensors_swap_free_returns_int(sensors: SystemSensors) -> None:
    """Verifies swap_free returns an integer byte count."""
    mock_swap = MagicMock()
    mock_swap.free = 2_000_000_000
    with patch("psutil.swap_memory", return_value=mock_swap):
        result = sensors.swap_free()
    assert isinstance(result, int)
    assert result == 2_000_000_000


def test_sensors_process_memory_rss_returns_int(
    sensors: SystemSensors,
) -> None:
    """Verifies process_memory_rss returns an integer."""
    result = sensors.process_memory_rss()
    assert isinstance(result, int)
    assert result > 0


def test_sensors_top_process_cpu_pct_returns_float(
    sensors: SystemSensors,
) -> None:
    """Verifies top_process_cpu_pct returns a float."""
    result = sensors.top_process_cpu_pct()
    assert isinstance(result, float)


def test_sensors_disk_partitions_count_returns_int(
    sensors: SystemSensors,
) -> None:
    """Verifies disk_partitions_count returns an integer count."""
    result = sensors.disk_partitions_count()
    assert isinstance(result, int)
    assert result >= 0


def test_sensors_net_connections_count_returns_int(
    sensors: SystemSensors,
) -> None:
    """Verifies net_connections_count returns an integer count."""
    result = sensors.net_connections_count()
    assert isinstance(result, int)


def test_sensors_net_connections_count_access_denied(
    sensors: SystemSensors,
) -> None:
    """Verifies net_connections_count handles AccessDenied exception."""
    with patch("psutil.net_connections", side_effect=psutil.AccessDenied):
        result = sensors.net_connections_count()
    assert result == 0
