"""الگوریتم‌های مسیریابی روی گراف بادی وزن‌دار.

این ماژول سه الگوریتم مسیریابی روی ``WindGraph`` پیاده‌سازی می‌کند:

- **Dijkstra:** الگوریتم کلاسیک کوتاه‌ترین مسیر. مناسب زمانی که هیچ
  تابع تخمین (heuristic) قابل‌اعتمادی وجود ندارد.

- **A*:** الگوریتم بهینه‌تر با استفاده از تابع تخمین فاصله هاورسین.
  سریع‌تر از Dijkstra در گراف‌های بزرگ با توزیع هندسی منظم.

- **smooth_dijkstra:** نسخه Dijkstra با جریمه تغییر جهت. علاوه بر هزینه
  بادی یال، هر بار که مسیر بیش از ``direction_penalty_threshold_deg`` درجه
  تغییر می‌کند یک جریمه ``direction_penalty`` به هزینه اضافه می‌شود.
  این باعث می‌شود مسیر یافت‌شده از مسیرهای پر-پیچ‌وخم پرهیز کند و
  جهت‌گیری پایدارتری داشته باشد — کاربرد: «سریع‌ترین بهینه با کمترین
  تغییر جهت».

**توابع تخمین و admissibility (اصلاح‌شده)**

تابع تخمین باید یک *کران پایین* روی هزینه باقی‌مانده باشد، وگرنه A* بهینه
نمی‌ماند. تخمین قبلی این ماژول فاصله هاورسین را بر *سرعت هوایی* تقسیم
می‌کرد و استدلال می‌کرد «سرعت زمینی هرگز از سرعت هوایی بیشتر نمی‌شود».
این استدلال نادرست است: مدل باد این پروژه سرعت زمینی را به‌صورت
``gs = sqrt(airspeed² − cross²) + along`` محاسبه می‌کند، پس **هر باد پشت**
سرعت زمینی را از سرعت هوایی بیشتر می‌کند و تخمین بیش‌برآورد می‌شد
(یعنی A* می‌توانست مسیر غیربهینه برگرداند).

تخمین فعلی بر پایه ``WindGraph.max_ground_speed_mps`` است: جمع سرعت هوایی و
بیشینه سرعت بادِ موجود در همان گراف. چون ``gs ≤ airspeed + |wind|`` همیشه
برقرار است، این تخمین هیچ‌گاه بیش‌تخمین نمی‌زند. برای معیارهای
``time``/``energy``/``balanced`` یک تخمین کافی است چون هر سه از زمان پرواز
کران پایین می‌گیرند (``energy = time × penalty`` با ``penalty ≥ 1`` و
``balanced`` ترکیب محدب همان دو)، و برای ``distance`` تخمین خودِ فاصله
بزرگ‌دایره است.
"""

from __future__ import annotations

import heapq
import math
from collections.abc import Callable

from pathfinding.cost import CRITERIA, InfeasibleEdgeError, air_heading_deg
from pathfinding.graph import GraphNode, WindGraph
from preprocessing.consistency import haversine_km

__all__ = [
    "dijkstra",
    "a_star",
    "smooth_dijkstra",
    "heuristic_lower_bound",
]


def heuristic_lower_bound(
    graph: WindGraph,
    end_id: str,
    criterion: str | None = None,
    airspeed_mps: float | None = None,
) -> Callable[[str], float]:
    """تابع تخمین *مجاز* (admissible) برای گراف و مقصد داده‌شده برمی‌گرداند.

    تابع بازگشتی برای یک شناسه گره، کران پایینی روی هزینه باقی‌مانده تا مقصد
    بر حسب واحد همان معیار می‌دهد.

    - ``criterion="distance"`` → فاصله بزرگ‌دایره (کیلومتر).
    - سه معیار دیگر → فاصله بزرگ‌دایره تقسیم بر **بیشینه سرعت زمینی ممکن**
      در گراف (ساعت).

    پارامتر ``airspeed_mps`` سرعت هوایی مورد استفاده در وزن‌دهی یال‌هاست. برای
    حفظ admissibility از بزرگ‌ترین مقدار میان مقدار داده‌شده و مقدار ثبت‌شده در
    خود گراف استفاده می‌شود: سرعت بزرگ‌تر ⇒ تخمین کوچک‌تر ⇒ هرگز بیش‌تخمین.

    پارامترها
    ----------
    graph : WindGraph
        گراف وزن‌دار بادی.
    end_id : str
        شناسه گره مقصد.
    criterion : str, اختیاری
        معیار بهینگی؛ در صورت ``None`` معیار ثبت‌شده در گراف استفاده می‌شود.
    airspeed_mps : float, اختیاری
        سرعت هوایی برای مقیاس‌دهی تخمین.

    برمی‌گرداند
    ----------
    Callable[[str], float]
        تابعی که برای هر شناسه گره یک کران پایین برمی‌گرداند. برای گره‌های
        ناشناخته مقدار ``0.0`` برمی‌گرداند (همیشه admissible).

    استثناها
    --------
    ValueError
        اگر ``criterion`` یکی از مقادیر شناخته‌شده نباشد.
    """
    resolved_criterion = graph.criterion if criterion is None else criterion
    if resolved_criterion not in CRITERIA:
        raise ValueError(
            f"Unknown criterion {resolved_criterion!r}; expected one of {CRITERIA}."
        )

    end_node: GraphNode | None = graph.get_node(end_id)
    if end_node is None:
        return lambda _node_id: 0.0

    if resolved_criterion == "distance":

        def distance_bound(node_id: str) -> float:
            node = graph.get_node(node_id)
            if node is None:
                return 0.0
            return haversine_km(node.lat, node.lon, end_node.lat, end_node.lon)

        return distance_bound

    # محافظه‌کارانه‌ترین ترکیب: بزرگ‌ترین سرعت هوایی شناخته‌شده + باد خود گراف.
    reference_airspeed = graph.config.airspeed_mps
    if airspeed_mps is not None:
        reference_airspeed = max(airspeed_mps, reference_airspeed)
    max_speed_kmh = graph.max_ground_speed_mps(reference_airspeed) * 3.6

    def time_bound(node_id: str) -> float:
        node = graph.get_node(node_id)
        if node is None or max_speed_kmh <= 0.0:
            return 0.0
        return haversine_km(node.lat, node.lon, end_node.lat, end_node.lon) / max_speed_kmh

    return time_bound


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

    # اولویت Queue: (cost, counter, node_id)
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
    airspeed_mps: float | None = None,
    criterion: str | None = None,
) -> tuple[list[str], float]:
    """الگوریتم A* برای یافتن کوتاه‌ترین مسیر با تابع تخمین هاورسین.

    تابع تخمین از ``heuristic_lower_bound`` گرفته می‌شود و بر پایه **بیشینه
    سرعت زمینی ممکن در همین گراف** (سرعت هوایی + بیشینه باد گراف) ساخته
    می‌شود، نه بر پایه سرعت هوایی تنها. دلیل: مدل باد این پروژه با باد پشت،
    سرعت زمینی را از سرعت هوایی بیشتر می‌کند؛ تقسیم بر سرعت هوایی تخمین را
    بیش‌برآورد می‌کند و A* دیگر بهینه نیست. با کران ``airspeed + |wind|``
    تخمین هیچ‌گاه بیش‌تخمین نمی‌زند و A* بهینه (optimal) می‌ماند.

    پارامترها
    ----------
    graph : WindGraph
        گراف وزن‌دار بادی.
    start_id : str
        شناسه گره مبدأ.
    end_id : str
        شناسه گره مقصد.
    airspeed_mps : float, اختیاری
        سرعت هوایی (متر بر ثانیه) برای مقیاس‌دهی تابع تخمین. در صورت ``None``
        از ``graph.config.airspeed_mps`` استفاده می‌شود (همان مقداری که یال‌ها
        با آن وزن‌دهی شده‌اند). اگر مقداری کوچک‌تر از سرعت ثبت‌شده گراف داده
        شود، برای حفظ admissibility مقدار بزرگ‌تر استفاده می‌شود.
    criterion : str, اختیاری
        معیار بهینگی تخمین. در صورت ``None`` معیار ثبت‌شده در گراف استفاده
        می‌شود؛ **باید** با معیاری که یال‌ها با آن وزن‌دهی شده‌اند یکی باشد،
        وگرنه تخمین در واحد اشتباه ساخته می‌شود. برای مسیریابی با معیار دیگر،
        ابتدا ``WindGraph.reweight`` را فراخوانی کنید.

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

    heuristic = heuristic_lower_bound(
        graph,
        end_id,
        criterion=criterion,
        airspeed_mps=airspeed_mps,
    )

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


def smooth_dijkstra(
    graph: WindGraph,
    start_id: str,
    end_id: str,
    direction_penalty: float = 0.05,
    direction_penalty_threshold_deg: float = 30.0,
    steering_airspeed_mps: float | None = None,
) -> tuple[list[str], float]:
    """Dijkstra با جریمه تغییر جهت — مسیر هموار با کمترین چرخش.

    علاوه بر هزینه بادی معمول هر یال، هر بار که زاویه انحراف بین جهت قطعه
    قبلی و قطعه فعلی از ``direction_penalty_threshold_deg`` بیشتر باشد،
    مقدار ``direction_penalty`` (به‌عنوان ساعت هزینه اضافی) به هزینه آن
    گذار افزوده می‌شود. این مکانیسم مسیرهای با جهت‌گیری پایدار را ترجیح
    می‌دهد بدون اینکه از مسیرهای فیزیکاً نادرست استفاده کند.

    حالت state ماشین جستجو: ``(node_id, prev_node_id)`` — نگه‌داری گره قبلی
    لازم است تا بردار جهت قطعه قبلی محاسبه شود.

    یال‌های عمودی (صعود/فرود) جریمه نمی‌گیرند: آزیموت یک گذار عمودی تعریف‌شده
    نیست (مبدأ و مقصدش دقیقاً یک مختصات دارند) و در گراف سه‌بعدی هر مسیر ناچار
    دو گذار عمودی دارد. اگر این دو گذار «تغییر جهت» شمرده می‌شدند، جریمه برای
    همه مسیرها یک مقدار ثابت می‌شد و هیچ اثری روی انتخاب مسیر نداشت — یعنی
    دقیقاً همان حالتی که در آن این الگوریتم بی‌اثر می‌شد.

    پارامترها
    ----------
    graph : WindGraph
        گراف وزن‌دار بادی.
    start_id : str
        شناسه گره مبدأ.
    end_id : str
        شناسه گره مقصد.
    direction_penalty : float
        جریمه اضافه‌شده (ساعت) به ازای هر تغییر جهت بیش از آستانه.
        مقدار پیش‌فرض ۰.۰۵ ساعت ≈ ۳ دقیقه تأخیر معادل.
    direction_penalty_threshold_deg : float
        آستانه تغییر جهت (درجه) که بالاتر از آن جریمه فعال می‌شود.
        مقدار پیش‌فرض ۳۰ درجه.
    steering_airspeed_mps : float, اختیاری
        اگر داده شود، «تغییر جهت» روی **سمت هوایی** سنجیده می‌شود (همان
        فرمانی که کنترلر باید نگه دارد) نه روی سمت مسیر روی زمین. تفاوت مهم
        است: با باد، سمت هوایی و سمت مسیر یکی نیستند و هواپیمایی که «بادسواری»
        می‌کند می‌تواند با یک فرمان ثابت، مسیر روی زمین را خمیده طی کند.
        بدون این پارامتر (پیش‌فرض)، همان رفتار قبلی (سمت مسیر) حفظ می‌شود.
        مقدار باید سرعت هوایی واقعی باشد؛ قطعه‌ای که نگه‌داشتن مسیرش با آن باد
        ممکن نیست (باد جانبی بیش از سرعت هوایی) به سمت مسیر خودش برمی‌گردد.

    برمی‌گرداند
    ----------
    tuple[list[str], float]
        لیست شناسه گره‌های مسیر (شامل مبدأ و مقصد) و هزینه کل مسیر
        (شامل جریمه‌های تغییر جهت).

    اگر مسیری وجود نداشته باشد، لیست خالی و هزینه ``inf`` برمی‌گرداند.
    """
    if start_id not in graph._nodes or end_id not in graph._nodes:
        return ([], math.inf)

    def _bearing_between(nid_a: str, nid_b: str) -> float | None:
        """آزیموت از گره a به b؛ ``None`` اگر گره وجود نداشته باشد."""
        na = graph.get_node(nid_a)
        nb = graph.get_node(nid_b)
        if na is None or nb is None:
            return None
        phi1, phi2 = math.radians(na.lat), math.radians(nb.lat)
        d_lambda = math.radians(nb.lon - na.lon)
        x = math.sin(d_lambda) * math.cos(phi2)
        y = (
            math.cos(phi1) * math.sin(phi2)
            - math.sin(phi1) * math.cos(phi2) * math.cos(d_lambda)
        )
        return (math.degrees(math.atan2(x, y)) + 360.0) % 360.0

    def _angular_diff(a: float, b: float) -> float:
        """اختلاف زاویه‌ای کوچک‌ترین بین دو آزیموت (۰ تا ۱۸۰ درجه)."""
        diff = abs(a - b) % 360.0
        return diff if diff <= 180.0 else 360.0 - diff

    def _steering_angle(nid_a: str, nid_b: str) -> float | None:
        """زاویه‌ای که تغییرش «تصحیح مسیر با موتور» شمرده می‌شود.

        پیش‌فرض: آزیموت مسیر روی زمین. با ``steering_airspeed_mps``:
        سمت هوایی همان قطعه، محاسبه‌شده از باد *گرهٔ شروع* قطعه — همان بادی که
        وزن یال را تعیین کرده است، پس معیار جریمه و مدل هزینه از یک منبع
        می‌آیند. اگر قطعه با آن باد پروازشدنی نباشد، به آزیموت زمین برمی‌گردد
        (چنین یالی در گراف وزن معتبر نمی‌گیرد).
        """
        bearing = _bearing_between(nid_a, nid_b)
        if bearing is None or steering_airspeed_mps is None:
            return bearing
        node_a = graph.get_node(nid_a)
        if node_a is None:
            return bearing
        try:
            heading, _ground_speed = air_heading_deg(
                bearing,
                node_a.wind_speed_mps,
                node_a.wind_direction_deg,
                steering_airspeed_mps,
            )
        except InfeasibleEdgeError:
            return bearing
        return heading

    # state = (current_node_id, previous_node_id_or_None)
    # این اجازه می‌دهد برای یک گره چندین حالت ورود با جهت‌های متفاوت داشته باشیم
    counter = 0
    # dist[(node, prev)] = بهترین هزینه رسیدن به node از جهت prev
    dist: dict[tuple[str, str | None], float] = {(start_id, None): 0.0}
    # prev_state[(node, prev)] = state قبلی برای بازسازی مسیر
    prev_state: dict[tuple[str, str | None], tuple[str, str | None] | None] = {
        (start_id, None): None
    }
    pq: list[tuple[float, int, str, str | None]] = [(0.0, counter, start_id, None)]
    visited: set[tuple[str, str | None]] = set()

    best_end_state: tuple[str, str | None] | None = None
    best_end_cost: float = math.inf

    while pq:
        d, _, u, prev_u = heapq.heappop(pq)
        state_u = (u, prev_u)
        if state_u in visited:
            continue
        visited.add(state_u)

        if u == end_id:
            if d < best_end_cost:
                best_end_cost = d
                best_end_state = state_u
            break  # Dijkstra: اولین بار رسیدن به مقصد، بهینه است

        for v in graph.get_neighbors(u):
            edge = graph.get_edge(u, v)
            if edge is None or math.isinf(edge.weight):
                continue

            edge_cost = edge.weight

            # جریمه تغییر جهت: اگر گره قبلی داریم، زاویه چرخش را محاسبه کن.
            # گذارهای عمودی از این محاسبه کنار گذاشته می‌شوند (آزیموت ندارند).
            prev_edge = graph.get_edge(prev_u, u) if prev_u is not None else None
            if (
                prev_u is not None
                and prev_edge is not None
                and not prev_edge.is_vertical
                and not edge.is_vertical
            ):
                heading_prev = _steering_angle(prev_u, u)
                heading_curr = _steering_angle(u, v)
                if heading_prev is not None and heading_curr is not None:
                    turn = _angular_diff(heading_prev, heading_curr)
                    if turn > direction_penalty_threshold_deg:
                        edge_cost += direction_penalty

            new_dist = d + edge_cost
            state_v = (v, u)
            if new_dist < dist.get(state_v, math.inf):
                dist[state_v] = new_dist
                prev_state[state_v] = state_u
                counter += 1
                heapq.heappush(pq, (new_dist, counter, v, u))

    if best_end_state is None:
        # بررسی آیا هیچ state مقصد در dist وجود دارد
        for key, cost in dist.items():
            if key[0] == end_id and cost < best_end_cost:
                best_end_cost = cost
                best_end_state = key

    if best_end_state is None or math.isinf(best_end_cost):
        return ([], math.inf)

    # بازسازی مسیر از state‌ها
    path: list[str] = []
    current_state: tuple[str, str | None] | None = best_end_state
    while current_state is not None:
        path.append(current_state[0])
        current_state = prev_state.get(current_state)
    path.reverse()

    return (path, best_end_cost)
