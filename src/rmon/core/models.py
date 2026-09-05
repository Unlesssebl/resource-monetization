"""
Core Data Transfer Objects (DTO) and Domain Models for RMon Platform.
Предоставляет типизированные контракты с методами .to_dict() и .from_dict(strict=False)
для безопасной градуальной интеграции между сервисами, очередями и DuckDB.
"""
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import uuid

@dataclass
class ListingItem:
    """Нормализованная карточка объявления с торговой площадки (Авито и др.)"""
    id: str
    title: str
    price_current: float
    target_id: str = ""
    source: str = "avito"
    price_original: float = 0.0
    location: str = ""
    seller: str = ""
    url: str = ""
    image_url: str = ""
    views_text: str = ""
    date_text: str = ""
    description: str = ""
    scraped_at: Optional[datetime] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any], strict: bool = False) -> "ListingItem":
        item_id = str(data.get("id") or data.get("item_id") or "")
        title = str(data.get("title") or "")
        try:
            price_current = float(data.get("price_current") or 0.0)
        except (ValueError, TypeError):
            price_current = 0.0

        try:
            price_original = float(data.get("price_original") or price_current)
        except (ValueError, TypeError):
            price_original = price_current

        scraped_at = data.get("scraped_at")
        if isinstance(scraped_at, str):
            try:
                scraped_at = datetime.fromisoformat(scraped_at)
            except Exception:
                scraped_at = None
        elif not isinstance(scraped_at, datetime):
            scraped_at = datetime.now(timezone.utc)

        return cls(
            id=item_id,
            title=title,
            price_current=price_current,
            target_id=str(data.get("target_id") or ""),
            source=str(data.get("source") or "avito"),
            price_original=price_original,
            location=str(data.get("location") or ""),
            seller=str(data.get("seller") or ""),
            url=str(data.get("url") or ""),
            image_url=str(data.get("image_url") or ""),
            views_text=str(data.get("views_text") or data.get("views") or ""),
            date_text=str(data.get("date_text") or data.get("date") or ""),
            description=str(data.get("description") or ""),
            scraped_at=scraped_at,
            raw_data=data if not strict else {}
        )

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if self.scraped_at:
            d["scraped_at"] = self.scraped_at.isoformat()
        # Для обратной совместимости с кодом, ожидающим item_id
        d["item_id"] = self.id
        return d


@dataclass
class MarketSummary:
    """Агрегированная рыночная статистика по целевому товару из DuckDB DataLake"""
    target_id: str
    total_items: int = 0
    median_price: float = 0.0
    p25_price: float = 0.0
    p75_price: float = 0.0
    min_price: float = 0.0
    max_price: float = 0.0

    @classmethod
    def from_dict(cls, data: Dict[str, Any], strict: bool = False) -> "MarketSummary":
        return cls(
            target_id=str(data.get("target_id") or ""),
            total_items=int(data.get("total_items") or 0),
            median_price=float(data.get("median_price") or 0.0),
            p25_price=float(data.get("p25_price") or 0.0),
            p75_price=float(data.get("p75_price") or 0.0),
            min_price=float(data.get("min_price") or 0.0),
            max_price=float(data.get("max_price") or 0.0)
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DealOpportunity:
    """Оцененная сделка с расчетом юнит-экономики, скорости ликвидности и оффером"""
    item: ListingItem
    market_median: float
    discount_pct: float
    liquidity_score: int = 50
    liquidity_tier: str = ""
    views_per_hour: float = 0.0
    hours_online: float = 0.0
    views_total: int = 0
    net_profit_rub: float = 0.0
    roi_pct: float = 0.0
    commission_rub: float = 0.0
    logistics_rub: float = 1000.0
    is_profitable: bool = False
    fast_cash_pitch: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any], strict: bool = False) -> "DealOpportunity":
        item_data = data.get("item")
        if isinstance(item_data, ListingItem):
            item = item_data
        elif isinstance(item_data, dict):
            item = ListingItem.from_dict(item_data, strict=strict)
        else:
            # Fallback: данные объявления могут лежать на верхнем уровне
            item = ListingItem.from_dict(data, strict=strict)

        return cls(
            item=item,
            market_median=float(data.get("market_median") or data.get("median_price") or 0.0),
            discount_pct=float(data.get("discount_pct") or data.get("discount_from_median_pct") or 0.0),
            liquidity_score=int(data.get("liquidity_score") or 50),
            liquidity_tier=str(data.get("liquidity_tier") or ""),
            views_per_hour=float(data.get("views_per_hour") or 0.0),
            hours_online=float(data.get("hours_online") or 0.0),
            views_total=int(data.get("views_total") or 0),
            net_profit_rub=float(data.get("net_profit_rub") or 0.0),
            roi_pct=float(data.get("roi_pct") or 0.0),
            commission_rub=float(data.get("commission_rub") or 0.0),
            logistics_rub=float(data.get("logistics_rub") or 1000.0),
            is_profitable=bool(data.get("is_profitable", False)),
            fast_cash_pitch=str(data.get("fast_cash_pitch") or "")
        )

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["item"] = self.item.to_dict()
        # Для плоской совместимости
        d["item_id"] = self.item.id
        d["title"] = self.item.title
        d["price_current"] = self.item.price_current
        d["url"] = self.item.url
        d["location"] = self.item.location
        d["seller"] = self.item.seller
        d["image_url"] = self.item.image_url
        return d


@dataclass
class AuditVerdict:
    """Результат нейросетевого аудита карточки лота (Gemini Flash / Ollama Qwen 2.5)"""
    item_id: str = ""
    is_scam_or_broken: bool = False
    risk_score: int = 50
    verdict: str = "CAUTION"  # "BUY" | "CAUTION" | "SKIP"
    detected_issues: List[str] = field(default_factory=list)
    concise_summary: str = ""
    model_used: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any], strict: bool = False) -> "AuditVerdict":
        return cls(
            item_id=str(data.get("item_id") or ""),
            is_scam_or_broken=bool(data.get("is_scam_or_broken", False)),
            risk_score=int(data.get("risk_score") or 50),
            verdict=str(data.get("verdict") or "CAUTION"),
            detected_issues=list(data.get("detected_issues") or []),
            concise_summary=str(data.get("concise_summary") or ""),
            model_used=str(data.get("model_used") or "")
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class QueueTask:
    """Унифицированный конверт задачи для брокера очередей (Redis / Memory fallback)"""
    task_type: str
    payload: Dict[str, Any]
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    priority: int = 0
    retry_count: int = 0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QueueTask":
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at)
            except Exception:
                created_at = datetime.now(timezone.utc)
        elif not isinstance(created_at, datetime):
            created_at = datetime.now(timezone.utc)

        return cls(
            task_id=str(data.get("task_id") or uuid.uuid4()),
            task_type=str(data.get("task_type") or "unknown"),
            payload=dict(data.get("payload") or {}),
            created_at=created_at,
            priority=int(data.get("priority") or 0),
            retry_count=int(data.get("retry_count") or 0)
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "payload": self.payload,
            "created_at": self.created_at.isoformat(),
            "priority": self.priority,
            "retry_count": self.retry_count
        }
