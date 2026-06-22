from __future__ import annotations

import json
import random
import hashlib
import re
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from xml.sax.saxutils import escape


SEED = 20260622
ROOT = Path(__file__).resolve().parent


@dataclass(frozen=True)
class CompanyFixture:
    ticker: str
    exchange: str
    legal_name: str
    short_name: str
    sector: str
    aliases: list[str]


@dataclass(frozen=True)
class EventTemplate:
    event: str
    sentiment: str
    title_en: str
    summary_en: str
    title_zh: str
    summary_zh: str


COMPANIES = [
    CompanyFixture("ALP", "SYN", "Alpine Robotics Holdings Ltd.", "Alpine Robotics", "Industrial Automation", ["Alpine Robotics", "ALP", "阿尔派机器人", "阿尔派"]),
    CompanyFixture("BRC", "SYN", "BrightRiver Cloud Systems Inc.", "BrightRiver Cloud", "Cloud Infrastructure", ["BrightRiver Cloud", "BRC", "明河云", "明河"]),
    CompanyFixture("HLS", "SYN", "HelioStorage Energy Group", "HelioStorage", "Energy Storage", ["HelioStorage", "HLS", "赫里奥储能", "赫里奥"]),
    CompanyFixture("NVM", "SYN", "NovaMed Devices Co.", "NovaMed", "Medical Devices", ["NovaMed", "NVM", "新维医疗", "新维"]),
    CompanyFixture("QNT", "SYN", "QuantHarbor Analytics PLC", "QuantHarbor", "Research Software", ["QuantHarbor Analytics", "QuantHarbor", "QNT", "量港分析", "量港"]),
    CompanyFixture("ORC", "SYN", "Orchid Circuit Materials Ltd.", "Orchid Circuit", "Electronic Materials", ["Orchid Circuit Materials", "Orchid Circuit", "ORC", "兰芯材料", "兰芯"]),
    CompanyFixture("VTL", "SYN", "VectorLoom Textiles Group", "VectorLoom", "Advanced Textiles", ["VectorLoom Textiles", "VectorLoom", "VTL", "纬织科技", "纬织"]),
    CompanyFixture("MTR", "SYN", "MetroSeed Foods Inc.", "MetroSeed Foods", "Consumer Staples", ["MetroSeed Foods", "MetroSeed", "MTR", "城籽食品", "城籽"]),
    CompanyFixture("SKY", "SYN", "SkyForge Components Co.", "SkyForge", "Aerospace Components", ["SkyForge Components", "SkyForge", "SKY", "天锻部件", "天锻"]),
    CompanyFixture("LUM", "SYN", "LumenBridge Optics Ltd.", "LumenBridge", "Optical Equipment", ["LumenBridge Optics", "LumenBridge", "LUM", "流明桥光学", "流明桥"]),
    CompanyFixture("PRM", "SYN", "PrimeVale Logistics SA", "PrimeVale", "Logistics", ["PrimeVale Logistics", "PrimeVale", "PRM", "启谷物流", "启谷"]),
    CompanyFixture("ECO", "SYN", "EcoMosaic Water Systems", "EcoMosaic", "Water Technology", ["EcoMosaic Water", "EcoMosaic", "ECO", "绿拼水务", "绿拼"]),
]

TEMPLATES = [
    EventTemplate("earnings", "positive", "{short} reports higher quarterly earnings after service demand improved", "{legal} said recurring service contracts strongly improved margins and revenue quality.", "{zh}公布季度业绩增长", "虚构公司{zh}表示服务需求改善，利润率明显提升。"),
    EventTemplate("merger_acquisition", "uncertain", "{short} signs non-binding merger discussion memo", "{short} said the merger talks may not result in a transaction and remain uncertain.", "{zh}签署非约束性并购讨论备忘录", "{zh}称并购讨论仍处早期，交易结果存在不确定性。"),
    EventTemplate("policy_regulation", "neutral", "{short} responds to new sector policy guidance", "{short} said the regulation changes are being evaluated with no material delivery change yet.", "{zh}回应新的监管政策指引", "{zh}表示正在评估政策规则，交付节奏暂无重大变化。"),
    EventTemplate("operations_product", "positive", "{short} launches maintenance platform for regional customers", "{short} released a product platform expected to improve support efficiency.", "{zh}推出区域客户维护平台", "{zh}发布产品平台，预计提升服务效率。"),
    EventTemplate("financing_capital", "uncertain", "{short} announces financing plan for module expansion", "{short} said the financing may support capacity work while timing remains uncertain.", "{zh}披露扩产融资计划", "{zh}称融资可能支持产能建设，但执行时间仍不确定。"),
    EventTemplate("litigation_penalty", "negative", "{short} warns about overseas litigation expense pressure", "{short} said litigation risk could create cost pressure, although operations continue.", "{zh}提示海外诉讼费用压力", "{zh}称诉讼风险可能带来费用压力，经营仍在继续。"),
    EventTemplate("governance_personnel", "neutral", "{short} appoints new chief operating officer", "{short} appointed a new operating chief after a planned leadership review.", "{zh}任命新的运营负责人", "{zh}在计划中的治理评估后任命新的运营负责人。"),
    EventTemplate("macro_market", "negative", "{short} notes softer macro market orders", "{short} said market demand weakened and orders may face pressure this quarter.", "{zh}提示宏观市场订单偏弱", "{zh}称市场需求走弱，本季度订单可能承压。"),
    EventTemplate("other", "neutral", "{short} publishes routine investor calendar update", "{short} published a routine calendar notice with no operational change.", "{zh}发布例行投资者日程更新", "{zh}发布例行日程通知，经营信息没有变化。"),
]

SOURCES = [
    ("synthetic-jsonl-desk", "Synthetic JSONL Desk", "fixture", timezone(timedelta(hours=8))),
    ("synthetic-import-wire", "Synthetic Import Wire", "import", timezone.utc),
    ("synthetic-announcement-board", "Synthetic Announcement Board", "official_announcement", timezone(timedelta(hours=9))),
    ("synthetic-evening-brief", "Synthetic Evening Brief", "other", timezone(timedelta(hours=-4))),
]


def render(template: str, company: CompanyFixture) -> str:
    zh_alias = company.aliases[-2]
    return template.format(
        short=company.short_name,
        legal=company.legal_name,
        ticker=company.ticker,
        zh=zh_alias,
    )


TRACKING_PARAMS = {"utm_source", "utm_medium", "utm_campaign"}


def normalize_display_text(value: str) -> str:
    text = unicodedata.normalize("NFKC", value)
    return re.sub(r"\s+", " ", text).strip()


def normalize_url(value: str) -> str:
    parts = urlsplit(value.strip())
    query = [
        (key, val)
        for key, val in parse_qsl(parts.query, keep_blank_values=True)
        if key.lower() not in TRACKING_PARAMS
    ]
    return urlunsplit(
        parts._replace(
            scheme=parts.scheme.lower(),
            netloc=parts.netloc.lower(),
            query=urlencode(query, doseq=True),
            fragment="",
        )
    )


def deterministic_hash(*parts: str) -> str:
    payload = "\n".join(normalize_display_text(part).lower() for part in parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def observation_id(record: dict[str, object]) -> str:
    article_id = str(record.get("article_id") or "")
    if article_id:
        return article_id
    published = datetime.fromisoformat(str(record["published_at"])).astimezone(UTC)
    return deterministic_hash(
        str(record["source_key"]),
        normalize_url(str(record["url"])),
        normalize_display_text(str(record["title"])),
        published.isoformat(),
    )


def make_record(index: int, company: CompanyFixture, template: EventTemplate, language: str) -> dict[str, object]:
    source_key, source_name, source_type, tz = SOURCES[index % len(SOURCES)]
    published = datetime(2026, 6, 18, 9, 0, tzinfo=tz) + timedelta(hours=index * 3)
    title = render(template.title_zh if language == "zh" else template.title_en, company)
    summary = render(template.summary_zh if language == "zh" else template.summary_en, company)
    summary = f"{summary} {'演示编号' if language == 'zh' else 'Demo case'} {index}."
    if index % 7 == 0:
        title = f"Ａ{title}  "
        summary = f"{summary}\n  {company.ticker}"
    return {
        "source_key": source_key,
        "source_name": source_name,
        "source_type": source_type,
        "article_id": "" if index in {11, 37, 53} else f"obs-{index:03d}",
        "url": f"https://demo.local/{source_key}/{company.ticker.lower()}-{index:03d}?utm_source=fixture&id={index}",
        "title": title,
        "summary": summary,
        "language": language,
        "published_at": published.isoformat(),
        "expected_event": template.event,
        "expected_sentiment": template.sentiment,
        "expected_ticker": company.ticker,
        "duplicate_kind": "unique",
    }


def build_records() -> list[dict[str, object]]:
    random.seed(SEED)
    records: list[dict[str, object]] = []
    unique_count = 42
    for index in range(unique_count):
        company = COMPANIES[index % len(COMPANIES)]
        template = TEMPLATES[index % len(TEMPLATES)]
        language = "zh" if index % 3 == 1 else "en"
        records.append(make_record(index + 1, company, template, language))

    exact_sources = list(records[:8])
    for offset, original in enumerate(exact_sources, start=1):
        duplicate = dict(original)
        duplicate["article_id"] = f"exact-{offset:03d}"
        duplicate["url"] = f"https://demo.local/exact/{offset:03d}?utm_campaign=dup"
        duplicate["source_key"] = SOURCES[(offset + 1) % len(SOURCES)][0]
        duplicate["source_name"] = SOURCES[(offset + 1) % len(SOURCES)][1]
        duplicate["duplicate_kind"] = "exact"
        records.append(duplicate)

    near_sources = list(records[8:18])
    for offset, original in enumerate(near_sources, start=1):
        near = dict(original)
        near["article_id"] = f"near-{offset:03d}"
        near["url"] = f"https://demo.local/near/{offset:03d}?utm_medium=near"
        near["title"] = f"{near['title']}."
        near["duplicate_kind"] = "near"
        records.append(near)

    malformed = [
        {"source_key": "synthetic-jsonl-desk", "source_name": "Synthetic JSONL Desk", "source_type": "fixture", "article_id": "bad-empty-title", "url": "https://demo.local/bad/empty", "title": "", "summary": "Empty title should reject.", "language": "en", "published_at": "2026-06-20T10:00:00+08:00", "duplicate_kind": "malformed"},
        {"source_key": "synthetic-jsonl-desk", "source_name": "Synthetic JSONL Desk", "source_type": "fixture", "article_id": "bad-language", "url": "https://demo.local/bad/lang", "title": "Invalid language", "summary": "Invalid language should reject.", "language": "fr", "published_at": "2026-06-20T10:00:00+08:00", "duplicate_kind": "malformed"},
        {"source_key": "synthetic-jsonl-desk", "source_name": "Synthetic JSONL Desk", "source_type": "fixture", "article_id": "bad-time", "url": "https://demo.local/bad/time", "title": "Invalid timestamp", "summary": "Invalid timestamp should reject.", "language": "en", "published_at": "not-a-date", "duplicate_kind": "malformed"},
        {"source_key": "synthetic-jsonl-desk", "source_name": "Synthetic JSONL Desk", "source_type": "fixture", "article_id": "bad-url", "url": "not a url", "title": "Invalid URL", "summary": "Invalid URL should reject.", "language": "en", "published_at": "2026-06-20T10:00:00+08:00", "duplicate_kind": "malformed"},
    ]
    records.extend(malformed)
    return records


def write_jsonl(records: list[dict[str, object]]) -> None:
    with (ROOT / "articles.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def write_companies() -> None:
    payload = [
        {
            "ticker": company.ticker,
            "exchange": company.exchange,
            "legal_name": company.legal_name,
            "short_name": company.short_name,
            "sector": company.sector,
            "aliases": company.aliases,
        }
        for company in COMPANIES
    ]
    (ROOT / "companies.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_labels(records: list[dict[str, object]], feed_records: list[dict[str, object]]) -> None:
    labels: dict[str, dict[str, object]] = {}
    canonical_by_exact = {
        f"exact-{index:03d}": observation_id(records[index - 1]) for index in range(1, 9)
    }
    canonical_by_near = {
        f"near-{index:03d}": observation_id(records[index + 7]) for index in range(1, 11)
    }
    for record in [*records, *feed_records]:
        obs_id = observation_id(record)
        duplicate_kind = str(record.get("duplicate_kind", "unique"))
        if duplicate_kind == "malformed":
            disposition = "rejected"
            canonical_id = None
            explanation = "malformed fixture observation rejected before canonical persistence"
        elif obs_id in canonical_by_exact:
            disposition = "exact_duplicate"
            canonical_id = canonical_by_exact[obs_id]
            explanation = "same normalized title, summary, and language as canonical observation"
        elif obs_id in canonical_by_near:
            disposition = "near_duplicate"
            canonical_id = canonical_by_near[obs_id]
            explanation = "near duplicate with deterministic high text similarity"
        else:
            disposition = "canonical"
            canonical_id = obs_id
            explanation = "first valid observation for this canonical article"
        label: dict[str, object] = {
            "disposition": disposition,
            "expected_canonical_observation_id": canonical_id,
            "expected_source_adapter": "local_feed"
            if obs_id.startswith("obs-10")
            else "jsonl_fixture",
            "fixture_group": duplicate_kind,
            "explanation": explanation,
        }
        if disposition != "rejected":
            label.update(
                {
                    "event": record["expected_event"],
                    "sentiment": record["expected_sentiment"],
                    "ticker": record["expected_ticker"],
                }
            )
        if disposition == "exact_duplicate":
            label["duplicate_type"] = "exact"
            label["expected_similarity_range"] = [1.0, 1.0]
        if disposition == "near_duplicate":
            label["duplicate_type"] = "near"
            label["expected_similarity_range"] = [0.86, 1.0]
        labels[obs_id] = label
    (ROOT / "expected_labels.json").write_text(
        json.dumps(labels, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def write_feed() -> list[dict[str, object]]:
    feed_records = [
        make_record(101, COMPANIES[0], TEMPLATES[3], "zh"),
        make_record(102, COMPANIES[4], TEMPLATES[6], "en"),
        make_record(103, COMPANIES[7], TEMPLATES[8], "en"),
        make_record(104, COMPANIES[10], TEMPLATES[7], "en"),
    ]
    feed_records[3]["summary"] = (
        "PrimeVale said market demand weakened and orders face risk pressure this quarter. "
        "Demo case 104."
    )
    items = []
    for record in feed_records:
        items.append(
            f"""    <item>
      <guid>{escape(str(record["article_id"]))}</guid>
      <title>{escape(str(record["title"]))}</title>
      <link>{escape(str(record["url"]))}</link>
      <description>{escape(str(record["summary"]))}</description>
      <pubDate>{datetime.fromisoformat(str(record["published_at"])).strftime("%a, %d %b %Y %H:%M:%S %z")}</pubDate>
    </item>"""
        )
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Synthetic Local Feed</title>
    <link>https://demo.local/feed</link>
    <description>Offline synthetic feed for Milestone 0 tests.</description>
{items}
  </channel>
</rss>
""".format(items="\n".join(items))
    (ROOT / "sample_feed.xml").write_text(xml, encoding="utf-8")
    return feed_records


def write_manifest(records: list[dict[str, object]]) -> None:
    valid = [record for record in records if record.get("duplicate_kind") != "malformed"]
    manifest = {
        "seed": SEED,
        "jsonl_observations": len(records),
        "valid_jsonl_observations": len(valid),
        "malformed_jsonl_observations": len(records) - len(valid),
        "exact_duplicate_observations": sum(1 for record in records if record.get("duplicate_kind") == "exact"),
        "near_duplicate_observations": sum(1 for record in records if record.get("duplicate_kind") == "near"),
        "companies": len(COMPANIES),
        "sources": len({record["source_key"] for record in records}),
        "event_categories": sorted({record["expected_event"] for record in valid}),
        "sentiment_categories": sorted({record["expected_sentiment"] for record in valid}),
    }
    (ROOT / "fixture_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def main() -> None:
    records = build_records()
    write_jsonl(records)
    write_companies()
    feed_records = write_feed()
    write_labels(records, feed_records)
    write_manifest(records)


if __name__ == "__main__":
    main()
