"""الگوریتم‌های مسیریابی روی گراف بادی وزن‌دار.

این ماژول دو الگوریتم مسیریابی کلاسیک را روی ``WindGraph`` پیاده‌سازی
می‌کند:

- **Dijkstra:** الگوریتم کلاسیک کوتاه‌ترین مسیر. مناسب زمانی که هیچ
  تابع تخمین (heuristic) قابل‌اعتمادی وجود ندارد.

- **A*:** الگوریتم بهینه‌تر با استفاده از تابع تخمین فاصله هاورسین.
  سریع‌تر از Dijkstra در گراف‌های بزرگ با توزیع هندسی منظم.

هر دو الگوریتم وزن یال‌ها را از ``EdgeData.weight`` (خروجی مدل هزینه
بادی) می‌خوانند و مسیر بهینه را به‌صورت لیست شناسه گره‌ها + هزینه کل
برمی‌گردانند.

هیچ placeholder یا مقدار فرضی در این ماژول استفاده نشده است.
"""

from __future__ import annotations

import heapq
import math

from pathfinding.graph import WindGraph
from preprocessing.consistency import haversine_km

__all__ = [
    "dijkstra",
    "a_star",
]


def dijkstra(
    graph: WindGraph,
    start_id: str,
    end_id: str,
) -> tuple[list[str], float]:
    """الگوریتم Dijkstra برای یافتن کوتاه‌ترین مسیر بر اساس وزن یال‌ها.

    پارامترها
    ----------
    graph : WindGraph
        گراف وزن‌دار بادی.
    start_id : str
        شناسه گره مبدأ.
    end_id : str
        شناسه گره مقصد.

    برمی‌گرداند
    ----------
    tuple[list[str], float]
        لیست شناسه گره‌های مسیر (شامل مبدأ و مقصد) و هزینه کل مسیر.

    اگر مسیری وجود نداشته باشد، لیست خالی و هزینه ``inf`` برمی‌گرداند.
    """
    if start_id not in graph._nodes or end_id not in graph._nodes:
        return ([], math.inf)

    # اولویت‌Queue: (cost, counter, node_id)
    counter = 0
    dist: dict[str, float] = {start_id: 0.0}
    prev: dict[str, str | None] = {start_id: None}
    pq: list[tuple[float, int, str]] = [(0.0, counter, start_id)]
    visited: set[str] = set()

    while pq:
        d, _, u = heapq.heappop(pq)
        if u in visited:
            continue
        visited.add(u)

        if u == end_id:
            break

        for v in graph.get_neighbors(u):
            edge = graph.get_edge(u, v)
            if edge is None or math.isinf(edge.weight):
                continue
            new_dist = d + edge.weight
            if new_dist < dist.get(v, math.inf):
                dist[v] = new_dist
                prev[v] = u
                counter += 1
                heapq.heappush(pq, (new_dist, counter, v))

    # بازسازی مسیر
    if end_id not in prev:
        return ([], math.inf)

    path: list[str] = []
    current: str | None = end_id
    while current is not None:
        path.append(current)
        current = prev[current]
    path.reverse()

    return (path, dist[end_id])


def a_star(
    graph: WindGraph,
    start_id: str,
    end_id: str,
    airspeed_mps: float = 50.0,
) -> tuple[list[str], float]:
    """الگوریتم A* برای یافتن کوتاه‌ترین مسیر با تابع تخمین هاورسین.

    تابع تخمین (heuristic) فاصله هاورسین بین گره فعلی و مقصد نهایی تقسیم
    بر حداکثر سرعت زمینی ممکن (``airspeed_mps * 3.6``) است. این تخمین
    همواره کمتر مساوی زمان واقعی پرواز باقی می‌ماند (چون سرعت زمینی
    واقعی همواره ≤ حداکثر سرعت ممکن)، بنابراین الگوریتم بهینه (optimal)
    باقی می‌ماند.

    پارامترها
    ----------
    graph : WindGraph
        گراف وزن‌دار بادی.
    start_id : str
        شناسه گره مبدأ.
    end_id : str
        شناسه گره مقصد.
    airspeed_mps : float
        سرعت هوایی (متر بر ثانیه) برای مقیاس‌دهی تابع تخمین. باید با
        ``CostModelConfig.airspeed_mps`` هماهنگ باشد.

    برمی‌گرداند
    ----------
    tuple[list[str], float]
        لیست شناسه گره‌های مسیر و هزینه کل.

    اگر مسیری وجود نداشته باشد، لیست خالی و هزینه ``inf`` برمی‌گرداند.
    """
    if start_id not in graph._nodes or end_id not in graph._nodes:
        return ([], math.inf)

    end_node = graph.get_node(end_id)
    if end_node is None:
        return ([], math.inf)

    # حداکثر سرعت زمینی ممکن (airspeed بدون باد) — کف پایین زمان پرواز
    max_speed_kmh = airspeed_mps * 3.6

    def heuristic(node_id: str) -> float:
        """تخمین زمان پرواز تا مقصد (ساعت) — admissible heuristic."""
        node = graph.get_node(node_id)
        if node is None:
            return 0.0
        dist_km = haversine_km(node.lat, node.lon, end_node.lat, end_node.lon)
        return dist_km / max_speed_kmh if max_speed_kmh > 0 else 0.0

    counter = 0
    g_score: dict[str, float] = {start_id: 0.0}
    prev: dict[str, str | None] = {start_id: None}
    f_start = heuristic(start_id)
    pq: list[tuple[float, int, str]] = [(f_start, counter, start_id)]
    visited: set[str] = set()

    while pq:
        _, _, u = heapq.heappop(pq)
        if u in visited:
            continue
        visited.add(u)

        if u == end_id:
            break

        for v in graph.get_neighbors(u):
            edge = graph.get_edge(u, v)
            if edge is None or math.isinf(edge.weight):
                continue
            tentative_g = g_score[u] + edge.weight
            if tentative_g < g_score.get(v, math.inf):
                g_score[v] = tentative_g
                prev[v] = u
                counter += 1
                f = tentative_g + heuristic(v)
                heapq.heappush(pq, (f, counter, v))

    # بازسازی مسیر
    if end_id not in prev:
        return ([], math.inf)

    path: list[str] = []
    current: str | None = end_id
    while current is not None:
        path.append(current)
        current = prev[current]
    path.reverse()

    return (path, g_score[end_id])
