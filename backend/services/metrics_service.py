"""
Servicio de métricas de telemetría y rendimiento del sistema.
Recolecta estadísticas de CPU, Memoria, Almacenamiento y Red desde
los adaptadores del sistema (o psutil como respaldo) y mantiene un histórico temporal.
"""
from collections import deque
from datetime import datetime, timezone, timedelta
import logging
import time
from typing import Deque, Dict, List, Optional, Any

import psutil
from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError

from ..config import get_settings
from ..database import SessionLocal
from ..models.database_models import MetricHistoryModel
from ..models.schemas import (
    SystemMetrics,
    CPUMetrics,
    MemoryMetrics,
    DiskMetrics,
    DiskPartitionMetrics,
    NetworkMetrics,
    MetricHistoryPoint,
    MetricsHistoryResponse,
)

logger = logging.getLogger(__name__)


def _get_demo_provider() -> Optional[Any]:
    """Importación perezosa del proveedor de datos demostrativos."""
    try:
        from backend.demo.demo_data import DemoDataProvider
        return DemoDataProvider
    except (ImportError, AttributeError):
        return None


def _get_system_adapter() -> Optional[Any]:
    """Importación perezosa del adaptador del sistema."""
    try:
        from backend.adapters.system_adapter import SystemAdapter
        return SystemAdapter
    except (ImportError, AttributeError):
        return None


class MetricsService:
    """
    Gestiona la obtención de telemetría en tiempo real y el histórico de rendimiento.
    """

    def __init__(self, history_maxlen: int = 1440) -> None:
        # Buffer circular en memoria para métricas históricas (hasta 24h a 1 muestra/minuto)
        self._history_buffer: Deque[MetricHistoryPoint] = deque(maxlen=history_maxlen)
        self._last_net_check_time: float = time.time()
        self._last_net_bytes_sent: int = 0
        self._last_net_bytes_recv: int = 0
        self._init_network_counters()

    def _init_network_counters(self) -> None:
        """Inicializa los contadores acumulativos de red para cálculo de tasas de transferencia."""
        try:
            net_io = psutil.net_io_counters()
            if net_io:
                self._last_net_bytes_sent = net_io.bytes_sent
                self._last_net_bytes_recv = net_io.bytes_recv
        except Exception as exc:
            logger.debug("No se pudieron inicializar los contadores de red psutil: %s", exc)

    def get_real_metrics(self) -> SystemMetrics:
        """
        Recolecta métricas reales del host actual utilizando adaptadores del sistema
        o introspección directa con psutil en caso de fallback.
        """
        adapter_cls = _get_system_adapter()
        if adapter_cls is not None:
            try:
                adapter = adapter_cls() if isinstance(adapter_cls, type) else adapter_cls
                # Intentar invocar los métodos más comunes del adaptador
                result = None
                if hasattr(adapter, "get_metrics"):
                    result = adapter.get_metrics()
                elif hasattr(adapter, "get_system_metrics"):
                    result = adapter.get_system_metrics()
                elif hasattr(adapter, "collect"):
                    result = adapter.collect()

                if isinstance(result, SystemMetrics):
                    self._record_history_point(result.cpu.total_percent, result.memory.percent, result.disk.root_usage_percent)
                    return result
                elif isinstance(result, dict) and "data" in result:
                    # Formato normalizado de adaptador
                    data = result["data"]
                    if isinstance(data, dict) and "cpu" in data:
                        metrics_obj = SystemMetrics(**data)
                        self._record_history_point(metrics_obj.cpu.total_percent, metrics_obj.memory.percent, metrics_obj.disk.root_usage_percent)
                        return metrics_obj
            except Exception as exc:
                logger.warning("Error consultando SystemAdapter, recurriendo a psutil nativo: %s", exc)

        # Fallback nativo directo con psutil
        return self._collect_psutil_metrics()

    def _collect_psutil_metrics(self) -> SystemMetrics:
        """Recolecta telemetría directa utilizando psutil."""
        uptime = time.time() - psutil.boot_time()

        # CPU
        cpu_total = psutil.cpu_percent(interval=None)
        cpu_per_core = psutil.cpu_percent(interval=None, percpu=True)
        cores_logical = psutil.cpu_count(logical=True) or 1
        cores_physical = psutil.cpu_count(logical=False) or 1
        try:
            load_avg = list(psutil.getloadavg())
        except (AttributeError, OSError):
            load_avg = [round(cpu_total / 100.0 * cores_logical, 2), 0.0, 0.0]

        cpu_metrics = CPUMetrics(
            total_percent=round(cpu_total, 2),
            per_cpu_percent=[round(p, 2) for p in cpu_per_core],
            cores_logical=cores_logical,
            cores_physical=cores_physical,
            load_avg=[round(l, 2) for l in load_avg],
        )

        # Memoria
        vm = psutil.virtual_memory()
        swap = psutil.swap_memory()
        mem_metrics = MemoryMetrics(
            total_bytes=vm.total,
            available_bytes=vm.available,
            used_bytes=vm.used,
            percent=round(vm.percent, 2),
            swap_total_bytes=swap.total,
            swap_used_bytes=swap.used,
            swap_percent=round(swap.percent, 2),
        )

        # Almacenamiento
        partitions_list: List[DiskPartitionMetrics] = []
        root_usage = 0.0
        root_total = 0
        root_used = 0
        root_free = 0

        for part in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(part.mountpoint)
                partition_item = DiskPartitionMetrics(
                    mountpoint=part.mountpoint,
                    filesystem=part.fstype,
                    total_bytes=usage.total,
                    used_bytes=usage.used,
                    free_bytes=usage.free,
                    percent=round(usage.percent, 2),
                )
                partitions_list.append(partition_item)
                if part.mountpoint == "/" or (root_total == 0 and part.mountpoint.startswith("/")):
                    root_usage = usage.percent
                    root_total = usage.total
                    root_used = usage.used
                    root_free = usage.free
            except (PermissionError, FileNotFoundError, OSError):
                continue

        if not partitions_list:
            # Fallback seguro para entornos de prueba
            try:
                usage = psutil.disk_usage("/")
                root_usage = usage.percent
                root_total = usage.total
                root_used = usage.used
                root_free = usage.free
                partitions_list.append(
                    DiskPartitionMetrics(
                        mountpoint="/",
                        filesystem="ext4",
                        total_bytes=usage.total,
                        used_bytes=usage.used,
                        free_bytes=usage.free,
                        percent=usage.percent,
                    )
                )
            except Exception:
                root_total = 50 * 1024 * 1024 * 1024
                root_used = 15 * 1024 * 1024 * 1024
                root_free = root_total - root_used
                root_usage = 30.0

        disk_metrics = DiskMetrics(
            root_usage_percent=round(root_usage, 2),
            total_bytes=root_total,
            used_bytes=root_used,
            free_bytes=root_free,
            partitions=partitions_list,
        )

        # Red
        now = time.time()
        elapsed = max(now - self._last_net_check_time, 0.001)
        net_io = psutil.net_io_counters()
        bytes_sent = net_io.bytes_sent if net_io else 0
        bytes_recv = net_io.bytes_recv if net_io else 0
        packets_sent = net_io.packets_sent if net_io else 0
        packets_recv = net_io.packets_recv if net_io else 0
        errin = net_io.errin if net_io else 0
        errout = net_io.errout if net_io else 0

        rx_rate_kb = max(0.0, (bytes_recv - self._last_net_bytes_recv) / 1024.0 / elapsed)
        tx_rate_kb = max(0.0, (bytes_sent - self._last_net_bytes_sent) / 1024.0 / elapsed)

        self._last_net_check_time = now
        self._last_net_bytes_sent = bytes_sent
        self._last_net_bytes_recv = bytes_recv

        net_metrics = NetworkMetrics(
            bytes_sent=bytes_sent,
            bytes_recv=bytes_recv,
            packets_sent=packets_sent,
            packets_recv=packets_recv,
            errors_in=errin,
            errors_out=errout,
        )

        metrics = SystemMetrics(
            uptime_seconds=round(uptime, 2),
            cpu=cpu_metrics,
            memory=mem_metrics,
            disk=disk_metrics,
            network=net_metrics,
        )

        self._record_history_point(cpu_metrics.total_percent, mem_metrics.percent, disk_metrics.root_usage_percent, rx_rate_kb, tx_rate_kb)
        return metrics

    def _record_history_point(
        self,
        cpu_percent: float,
        memory_percent: float,
        disk_percent: float,
        rx_kb: float = 120.5,
        tx_kb: float = 85.2,
    ) -> None:
        """Registra un punto de telemetría en el búfer circular."""
        point = MetricHistoryPoint(
            timestamp=datetime.now(timezone.utc),
            cpu_percent=round(cpu_percent, 2),
            memory_percent=round(memory_percent, 2),
            disk_percent=round(disk_percent, 2),
            network_rx_kb=round(rx_kb, 2),
            network_tx_kb=round(tx_kb, 2),
        )
        self._history_buffer.append(point)
        retention_cutoff = point.timestamp - timedelta(days=7)
        try:
            with SessionLocal() as db:
                db.add(
                    MetricHistoryModel(
                        timestamp=point.timestamp,
                        cpu_percent=point.cpu_percent,
                        memory_percent=point.memory_percent,
                        disk_percent=point.disk_percent,
                        network_rx_kb=point.network_rx_kb,
                        network_tx_kb=point.network_tx_kb,
                    )
                )
                db.execute(
                    delete(MetricHistoryModel).where(MetricHistoryModel.timestamp < retention_cutoff)
                )
                db.commit()
        except SQLAlchemyError:
            logger.exception("No se pudo persistir una muestra de telemetría.")

    def get_metrics(self) -> SystemMetrics:
        """
        Retorna las métricas actuales del sistema, respetando el modo demostración.
        """
        settings = get_settings()
        if settings.DEMO_MODE:
            provider = _get_demo_provider()
            if provider is not None and hasattr(provider, "get_system_metrics"):
                demo_data = provider.get_system_metrics()
                if isinstance(demo_data, SystemMetrics):
                    return demo_data
                elif isinstance(demo_data, dict):
                    cpu_data = demo_data["cpu"]
                    memory_data = demo_data["memory"]
                    disk_data = demo_data["disk"]
                    network_data = demo_data["network"]

                    memory_total = int(memory_data["total_gb"] * 1024**3)
                    memory_used = int(memory_data["used_gb"] * 1024**3)
                    disk_partitions = [
                        DiskPartitionMetrics(
                            mountpoint=partition["mount"],
                            filesystem="demo",
                            total_bytes=int(partition["total_gb"] * 1024**3),
                            used_bytes=int(partition["used_gb"] * 1024**3),
                            free_bytes=int((partition["total_gb"] - partition["used_gb"]) * 1024**3),
                            percent=partition["percent"],
                        )
                        for partition in disk_data["partitions"]
                    ]
                    root_partition = next(
                        (partition for partition in disk_partitions if partition.mountpoint == "/"),
                        disk_partitions[0],
                    )
                    return SystemMetrics(
                        uptime_seconds=demo_data["uptime_seconds"],
                        cpu=CPUMetrics(
                            total_percent=cpu_data["percent"],
                            per_cpu_percent=[cpu_data["percent"]] * cpu_data["count"],
                            cores_logical=cpu_data["count"],
                            cores_physical=cpu_data["count"],
                            load_avg=cpu_data["load_avg"],
                        ),
                        memory=MemoryMetrics(
                            total_bytes=memory_total,
                            available_bytes=max(0, memory_total - memory_used),
                            used_bytes=memory_used,
                            percent=memory_data["percent"],
                            swap_total_bytes=0,
                            swap_used_bytes=0,
                            swap_percent=0,
                        ),
                        disk=DiskMetrics(
                            root_usage_percent=root_partition.percent,
                            total_bytes=root_partition.total_bytes,
                            used_bytes=root_partition.used_bytes,
                            free_bytes=root_partition.free_bytes,
                            partitions=disk_partitions,
                        ),
                        network=NetworkMetrics(
                            bytes_sent=network_data["bytes_sent"],
                            bytes_recv=network_data["bytes_recv"],
                            packets_sent=network_data["packets_sent"],
                            packets_recv=network_data["packets_recv"],
                            errors_in=network_data.get("errors_in", 0),
                            errors_out=network_data.get("errors_out", 0),
                        ),
                    )

            # Generación sintética si DemoDataProvider no está disponible aún
            return self._generate_fallback_demo_metrics()

        return self.get_real_metrics()

    def get_history(self, range_str: str = "1h") -> MetricsHistoryResponse:
        """
        Retorna el histórico de telemetría para el rango temporal solicitado (1h, 6h, 24h, 7d).
        """
        settings = get_settings()
        if settings.DEMO_MODE:
            provider = _get_demo_provider()
            if provider is not None and hasattr(provider, "get_metrics_history"):
                demo_history = provider.get_metrics_history(range_str)
                if isinstance(demo_history, MetricsHistoryResponse):
                    return demo_history
                elif isinstance(demo_history, dict):
                    return MetricsHistoryResponse(**demo_history)
                elif isinstance(demo_history, list):
                    return MetricsHistoryResponse(range=range_str, points=demo_history)

            return self._generate_fallback_history(range_str)

        range_durations = {
            "1h": timedelta(hours=1),
            "6h": timedelta(hours=6),
            "24h": timedelta(hours=24),
            "7d": timedelta(days=7),
        }
        if range_str not in range_durations:
            raise ValueError(f"Rango de métricas no válido: {range_str}")

        cutoff = datetime.now(timezone.utc) - range_durations[range_str]
        try:
            with SessionLocal() as db:
                rows = db.execute(
                    select(MetricHistoryModel)
                    .where(MetricHistoryModel.timestamp >= cutoff)
                    .order_by(MetricHistoryModel.timestamp)
                ).scalars().all()
        except SQLAlchemyError:
            logger.exception("No se pudo consultar el histórico persistido de métricas.")
            raise
        points = [
            MetricHistoryPoint(
                timestamp=row.timestamp.replace(tzinfo=timezone.utc) if row.timestamp.tzinfo is None else row.timestamp,
                cpu_percent=row.cpu_percent,
                memory_percent=row.memory_percent,
                disk_percent=row.disk_percent,
                network_rx_kb=row.network_rx_kb,
                network_tx_kb=row.network_tx_kb,
            )
            for row in rows
        ]
        return MetricsHistoryResponse(range=range_str, points=points)

    def _generate_fallback_demo_metrics(self) -> SystemMetrics:
        """Métricas sintéticas de respaldo para modo demostración."""
        return SystemMetrics(
            uptime_seconds=86400.0 * 14.5,
            cpu=CPUMetrics(
                total_percent=24.5,
                per_cpu_percent=[22.0, 27.0, 23.5, 25.5],
                cores_logical=4,
                cores_physical=2,
                load_avg=[0.45, 0.52, 0.48],
            ),
            memory=MemoryMetrics(
                total_bytes=8 * 1024 * 1024 * 1024,
                available_bytes=4600000000,
                used_bytes=3989744640,
                percent=46.4,
                swap_total_bytes=2 * 1024 * 1024 * 1024,
                swap_used_bytes=104857600,
                swap_percent=4.8,
            ),
            disk=DiskMetrics(
                root_usage_percent=58.2,
                total_bytes=120 * 1024 * 1024 * 1024,
                used_bytes=69840000000,
                free_bytes=50160000000,
                partitions=[
                    DiskPartitionMetrics(
                        mountpoint="/",
                        filesystem="ext4",
                        total_bytes=120 * 1024 * 1024 * 1024,
                        used_bytes=69840000000,
                        free_bytes=50160000000,
                        percent=58.2,
                    )
                ],
            ),
            network=NetworkMetrics(
                bytes_sent=1542300000,
                bytes_recv=3421500000,
                packets_sent=1240500,
                packets_recv=2584100,
                errors_in=0,
                errors_out=0,
            ),
        )

    def _generate_fallback_history(self, range_str: str) -> MetricsHistoryResponse:
        """Genera datos históricos sintéticos para demostración."""
        points: List[MetricHistoryPoint] = []
        now = datetime.now(timezone.utc)
        count = 30
        delta_minutes = 2 if range_str == "1h" else 12 if range_str == "6h" else 48 if range_str == "24h" else 336

        for i in range(count, -1, -1):
            pt_time = now - timedelta(minutes=i * delta_minutes)
            # Oscilación suave para graficar
            cpu_val = 20.0 + (i % 7) * 3.5 + ((i * 3) % 5)
            mem_val = 45.0 + (i % 4) * 1.2
            disk_val = 58.0 + (i * 0.05)
            rx_val = 80.0 + (i % 5) * 40.0
            tx_val = 40.0 + (i % 3) * 25.0
            points.append(
                MetricHistoryPoint(
                    timestamp=pt_time,
                    cpu_percent=round(min(cpu_val, 98.0), 2),
                    memory_percent=round(min(mem_val, 99.0), 2),
                    disk_percent=round(min(disk_val, 99.0), 2),
                    network_rx_kb=round(rx_val, 2),
                    network_tx_kb=round(tx_val, 2),
                )
            )
        return MetricsHistoryResponse(range=range_str, points=points)

metrics_service = MetricsService()
