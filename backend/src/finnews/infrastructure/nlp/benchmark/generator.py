from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from finnews.domain.enums import EventType, SentimentLabel
from finnews.infrastructure.nlp.benchmark.models import (
    CHALLENGE_FLAGS,
    DATASET_ID,
    DATASET_VERSION,
    GENERATOR_VERSION,
    BenchmarkRecord,
)
from finnews.infrastructure.normalization import comparison_text

EVENTS = tuple(EventType)
SENTIMENTS = tuple(SentimentLabel)
SPLIT_BY_FAMILY = {
    "tf-00": "train",
    "tf-01": "train",
    "tf-02": "train",
    "tf-03": "train",
    "tf-04": "train",
    "tf-05": "train",
    "tf-06": "validation",
    "tf-07": "validation",
    "tf-08": "validation",
    "tf-09": "test",
    "tf-10": "test",
    "tf-11": "test",
}
LANGUAGE_BY_FAMILY = {
    "tf-00": "zh",
    "tf-01": "zh",
    "tf-02": "zh",
    "tf-03": "zh",
    "tf-04": "en",
    "tf-05": "en",
    "tf-06": "zh",
    "tf-07": "zh",
    "tf-08": "en",
    "tf-09": "zh",
    "tf-10": "zh",
    "tf-11": "en",
}
SOURCE_TYPES = ("synthetic_wire", "synthetic_exchange_notice", "synthetic_research_note")
REAL_COMPANY_DENYLIST = {
    "apple",
    "microsoft",
    "amazon",
    "tesla",
    "nvidia",
    "google",
    "alphabet",
    "meta",
    "alibaba",
    "tencent",
    "baidu",
    "byd",
    "贵州茅台",
    "腾讯",
    "阿里巴巴",
    "百度",
    "宁德时代",
    "比亚迪",
}


@dataclass(frozen=True)
class FictionalCompany:
    company_id: str
    ticker: str
    zh_name: str
    en_name: str
    industry_zh: str
    industry_en: str


COMPANIES = tuple(
    FictionalCompany(
        company_id=f"fc-{index + 1:03d}",
        ticker=f"F{chr(65 + (index // 10))}{index % 10}{chr(75 + (index % 12))}",
        zh_name=zh_name,
        en_name=en_name,
        industry_zh=industry_zh,
        industry_en=industry_en,
    )
    for index, (zh_name, en_name, industry_zh, industry_en) in enumerate(
        [
            ("澜石微电", "Lanstone Microgrid", "智能电网", "smart grid"),
            ("星河药械", "Stellar Medworks", "医疗器械", "medical devices"),
            ("远澜云服", "Farwave Cloud", "云服务", "cloud services"),
            ("青杉储能", "Cedar Storage", "储能设备", "energy storage"),
            ("海棠物流", "Harborleaf Logistics", "智慧物流", "smart logistics"),
            ("凌川材料", "Ridgeflow Materials", "新材料", "advanced materials"),
            ("北辰数科", "Northstar Data", "数据软件", "data software"),
            ("望舒机器人", "Moonpath Robotics", "工业机器人", "industrial robotics"),
            ("锦帆食品", "Goldsail Foods", "食品加工", "food processing"),
            ("曜晶显示", "Brightcell Display", "显示面板", "display panels"),
            ("云岭环保", "Cloudridge Ecology", "环保服务", "environmental services"),
            ("银桐租赁", "Silverbirch Leasing", "设备租赁", "equipment leasing"),
            ("晨越航电", "Dawnreach Avionics", "航空电子", "avionics"),
            ("松境家居", "Pineview Home", "智能家居", "smart home"),
            ("琥珀水务", "Amberwell Water", "水务运营", "water utilities"),
            ("逐光电缆", "Suntrail Cable", "电力电缆", "power cables"),
            ("霁蓝安防", "Clearblue Safety", "工业安防", "industrial safety"),
            ("鸿屿农科", "Redisle Agritech", "农业科技", "agricultural technology"),
            ("清梧教育", "Clearwutong Learning", "职业教育", "vocational education"),
            ("弦舟传媒", "Stringboat Media", "数字传媒", "digital media"),
            ("岚泉饮品", "Mistwell Drinks", "消费饮品", "consumer beverages"),
            ("卓晟装备", "Summitforge Equipment", "专用设备", "specialized equipment"),
            ("衡岳软件", "Mountscale Software", "企业软件", "enterprise software"),
            ("星桥通信", "Starbridge Telecom", "通信设备", "telecom equipment"),
            ("翰源出版", "Inkwell Publishing", "文化出版", "publishing"),
            ("森序检测", "Forestline Testing", "检测服务", "testing services"),
            ("韶光照明", "Timelight Lighting", "节能照明", "efficient lighting"),
            ("砺石机械", "Grindstone Machinery", "工程机械", "construction machinery"),
            ("沐川纺织", "Brookvale Textile", "功能纺织", "technical textiles"),
            ("循星仪表", "Orbitmark Instruments", "仪器仪表", "precision instruments"),
            ("棠溪生物", "Pearcreek Bio", "合成生物", "synthetic biology"),
            ("川曜热能", "Riverglow Thermal", "热能设备", "thermal systems"),
            ("观澜支付", "Viewtide Payments", "支付技术", "payment technology"),
            ("知遥咨询", "Farsage Advisory", "产业咨询", "industry advisory"),
            ("砚湖化工", "Inkpond Chemicals", "精细化工", "specialty chemicals"),
            ("拂晓电驱", "Daybreak Drives", "电驱系统", "electric drives"),
        ]
    )
)

EVENT_TEXT = {
    EventType.EARNINGS: ("业绩", "results"),
    EventType.MERGER_ACQUISITION: ("并购", "merger"),
    EventType.POLICY_REGULATION: ("监管政策", "policy review"),
    EventType.OPERATIONS_PRODUCT: ("产品运营", "product operations"),
    EventType.FINANCING_CAPITAL: ("融资资本", "financing"),
    EventType.LITIGATION_PENALTY: ("诉讼处罚", "litigation"),
    EventType.GOVERNANCE_PERSONNEL: ("治理人事", "governance"),
    EventType.MACRO_MARKET: ("宏观市场", "macro market"),
    EventType.OTHER: ("综合事项", "general update"),
}
SENTIMENT_TEXT = {
    SentimentLabel.POSITIVE: ("改善", "improved"),
    SentimentLabel.NEUTRAL: ("平稳", "steady"),
    SentimentLabel.NEGATIVE: ("承压", "pressured"),
    SentimentLabel.UNCERTAIN: ("不确定", "ambiguous"),
}


def benchmark_dir(root: Path) -> Path:
    return root / "data" / "evaluation" / DATASET_ID


def build_benchmark() -> list[BenchmarkRecord]:
    records: list[BenchmarkRecord] = []
    started = datetime(2026, 1, 5, 9, 0, tzinfo=UTC)
    event_list = list(EVENTS)
    sentiment_list = list(SENTIMENTS)
    for family_index, family_id in enumerate(SPLIT_BY_FAMILY):
        language = LANGUAGE_BY_FAMILY[family_id]
        split = SPLIT_BY_FAMILY[family_id]
        for event_index, event in enumerate(event_list):
            for sentiment_index, sentiment in enumerate(sentiment_list):
                group_index = event_index * len(sentiment_list) + sentiment_index
                company = COMPANIES[(family_index * 3 + group_index) % len(COMPANIES)]
                story_group_id = f"sg-{family_id}-{event.value}-{sentiment.value}"
                for paraphrase_id in range(3):
                    ordinal = (
                        family_index * len(event_list) * len(sentiment_list) * 3
                        + group_index * 3
                        + paraphrase_id
                    )
                    challenge_flags = _challenge_flags(family_index, group_index, paraphrase_id)
                    record = _record(
                        family_id=family_id,
                        family_index=family_index,
                        language=language,
                        split=split,
                        event=event,
                        sentiment=sentiment,
                        company=company,
                        story_group_id=story_group_id,
                        paraphrase_id=paraphrase_id,
                        published_at=started + timedelta(hours=ordinal),
                        challenge_flags=challenge_flags,
                    )
                    _reject_real_company_names(record)
                    records.append(record)
    _reject_duplicate_records(records)
    return records


def write_benchmark(output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    records = build_benchmark()
    records_path = output_dir / "records.jsonl"
    records_path.write_text(
        "\n".join(record.model_dump_json() for record in records) + "\n",
        encoding="utf-8",
    )
    dataset_hash = _file_sha256(records_path)
    split_hashes = {
        split: _hash_records([record for record in records if record.split == split])
        for split in ("train", "validation", "test")
    }
    label_distribution = _label_distribution(records)
    manifest = {
        "dataset_id": DATASET_ID,
        "dataset_version": DATASET_VERSION,
        "generator_version": GENERATOR_VERSION,
        "record_count": len(records),
        "dataset_sha256": dataset_hash,
        "split_hashes": split_hashes,
        "language_counts": dict(sorted(Counter(record.language for record in records).items())),
        "split_counts": dict(sorted(Counter(record.split for record in records).items())),
        "event_labels": [event.value for event in EVENTS],
        "sentiment_labels": [sentiment.value for sentiment in SENTIMENTS],
        "synthetic_only": True,
        "label_source": "generator_defined_synthetic_gold",
        "not_investment_advice": True,
        "no_live_source_content": True,
    }
    files = {
        "manifest.json": manifest,
        "label_distribution.json": label_distribution,
        "split_hashes.json": split_hashes,
        "generation_config.json": _generation_config(),
        "test_lock.json": {
            "dataset_id": DATASET_ID,
            "dataset_version": DATASET_VERSION,
            "test_record_count": sum(1 for record in records if record.split == "test"),
            "test_split_sha256": split_hashes["test"],
            "record_ids_sha256": _hash_text(
                "\n".join(record.record_id for record in records if record.split == "test")
            ),
        },
    }
    for name, payload in files.items():
        (output_dir / name).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return manifest


def load_records(dataset_dir: Path) -> list[BenchmarkRecord]:
    path = dataset_dir / "records.jsonl"
    return [
        BenchmarkRecord.model_validate_json(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _record(
    *,
    family_id: str,
    family_index: int,
    language: str,
    split: str,
    event: EventType,
    sentiment: SentimentLabel,
    company: FictionalCompany,
    story_group_id: str,
    paraphrase_id: int,
    published_at: datetime,
    challenge_flags: list[str],
) -> BenchmarkRecord:
    event_word_zh, event_word_en = EVENT_TEXT[event]
    sentiment_word_zh, sentiment_word_en = SENTIMENT_TEXT[sentiment]
    difficulty = "hard" if challenge_flags else ("medium" if paraphrase_id == 1 else "easy")
    source_type = SOURCE_TYPES[(family_index + paraphrase_id) % len(SOURCE_TYPES)]
    if language == "zh":
        title = _zh_title(company.zh_name, company.ticker, event_word_zh, sentiment_word_zh)
        summary = _zh_summary(
            company.zh_name,
            company.ticker,
            company.industry_zh,
            event_word_zh,
            sentiment_word_zh,
            paraphrase_id,
            challenge_flags,
        )
        industry = company.industry_zh
    else:
        title = _en_title(company.en_name, company.ticker, event_word_en, sentiment_word_en)
        summary = _en_summary(
            company.en_name,
            company.ticker,
            company.industry_en,
            event_word_en,
            sentiment_word_en,
            paraphrase_id,
            challenge_flags,
        )
        industry = company.industry_en
    record_id = f"m2a-{family_id}-{event.value}-{sentiment.value}-p{paraphrase_id}"
    return BenchmarkRecord(
        record_id=record_id,
        language=language,  # type: ignore[arg-type]
        title=title,
        summary=summary,
        combined_text=f"TITLE: {title}\nSUMMARY: {summary}",
        event_label=event,
        sentiment_label=sentiment,
        company_id=company.company_id,
        fictional_ticker=company.ticker,
        industry=industry,
        source_type=source_type,  # type: ignore[arg-type]
        published_at=published_at,
        template_family_id=family_id,
        story_group_id=story_group_id,
        paraphrase_id=paraphrase_id,
        split=split,  # type: ignore[arg-type]
        difficulty=difficulty,  # type: ignore[arg-type]
        challenge_flags=challenge_flags,
    )


def _zh_title(company: str, ticker: str, event_word: str, sentiment_word: str) -> str:
    return f"{company}（{ticker}）披露{event_word}进展，基调{sentiment_word}"


def _zh_summary(
    company: str,
    ticker: str,
    industry: str,
    event_word: str,
    sentiment_word: str,
    paraphrase_id: int,
    challenge_flags: list[str],
) -> str:
    stems = [
        f"{company}称，围绕{industry}业务的{event_word}事项已进入阶段性披露，管理层描述为{sentiment_word}。",
        f"这家虚构企业表示，{ticker}相关公告只用于合成评测，不代表真实交易建议。",
        "后续安排仍以内部模拟计划为准，摘要不包含任何真实新闻语句。",
    ]
    if paraphrase_id == 1:
        stems[0] = f"{company}更新{industry}板块的{event_word}信息，整体措辞保持{sentiment_word}。"
    elif paraphrase_id == 2:
        stems[0] = f"围绕{event_word}主题，{company}给出{sentiment_word}口径并列示若干模拟指标。"
    return " ".join(stems + _zh_challenge_text(challenge_flags))


def _en_title(company: str, ticker: str, event_word: str, sentiment_word: str) -> str:
    return f"{company} ({ticker}) posts {sentiment_word} {event_word} update"


def _en_summary(
    company: str,
    ticker: str,
    industry: str,
    event_word: str,
    sentiment_word: str,
    paraphrase_id: int,
    challenge_flags: list[str],
) -> str:
    stems = [
        (
            f"{company} described a synthetic {event_word} item in its {industry} unit "
            f"with a {sentiment_word} tone."
        ),
        (
            f"The fictional ticker {ticker} is included only for benchmark evaluation "
            "and is not a trading signal."
        ),
        "The summary is original synthetic text and contains no copied live-source material.",
    ]
    if paraphrase_id == 1:
        stems[0] = (
            f"{company} issued a generated note on {event_word}, keeping the assessment "
            f"{sentiment_word}."
        )
    elif paraphrase_id == 2:
        stems[0] = (
            f"The synthetic story frames {company}'s {event_word} situation as {sentiment_word}."
        )
    return " ".join(stems + _en_challenge_text(challenge_flags))


def _zh_challenge_text(flags: list[str]) -> list[str]:
    mapping = {
        "negation": "文本说明并非所有风险都已消除。",
        "uncertainty": "管理层使用可能、预计等不确定措辞。",
        "mixed_signal": "同一摘要同时包含有利进展和成本压力。",
        "hypothetical_or_plan": "部分安排仍是计划而非已完成事项。",
        "class_overlap": "事项与相邻事件类别存在表述重叠。",
        "numerical_reversal": "模拟指标先升后降，方向需要结合上下文。",
        "cross_sentence_context": "判断需要连接前后两句话。",
        "short_text": "简讯信息有限。",
        "long_text": "摘要额外列出多个背景条件和限制。",
        "alias_or_ticker": "公司简称与虚构代码交替出现。",
        "neutral_boilerplate": "段落含有标准化免责声明。",
        "low_information": "可用信息较少，结论保持克制。",
    }
    return [mapping[flag] for flag in flags]


def _en_challenge_text(flags: list[str]) -> list[str]:
    mapping = {
        "negation": "The text says not every risk has been removed.",
        "uncertainty": "Management uses may, expected, and cautious language.",
        "mixed_signal": "The same note combines progress with cost pressure.",
        "hypothetical_or_plan": "Some actions remain planned rather than completed.",
        "class_overlap": "The wording overlaps with a neighboring event class.",
        "numerical_reversal": "A synthetic metric rises first and then reverses.",
        "cross_sentence_context": "The label requires linking two sentences.",
        "short_text": "The brief item has limited information.",
        "long_text": "The summary adds several background conditions and limits.",
        "alias_or_ticker": "The fictional ticker and company alias both appear.",
        "neutral_boilerplate": "The paragraph includes neutral boilerplate.",
        "low_information": "Available information is sparse and restrained.",
    }
    return [mapping[flag] for flag in flags]


def _challenge_flags(family_index: int, group_index: int, paraphrase_id: int) -> list[str]:
    if paraphrase_id != 2:
        return []
    first = CHALLENGE_FLAGS[(family_index + group_index) % len(CHALLENGE_FLAGS)]
    if group_index % 6 == 0:
        second = CHALLENGE_FLAGS[(family_index + group_index + 5) % len(CHALLENGE_FLAGS)]
        if second != first:
            return sorted([first, second])
    return [first]


def _reject_real_company_names(record: BenchmarkRecord) -> None:
    text = comparison_text(f"{record.title} {record.summary}")
    for name in REAL_COMPANY_DENYLIST:
        if comparison_text(name) in text:
            raise ValueError(f"real-company denylist hit in {record.record_id}: {name}")


def _reject_duplicate_records(records: list[BenchmarkRecord]) -> None:
    ids = [record.record_id for record in records]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate record_id generated")
    normalized = [comparison_text(record.combined_text) for record in records]
    if len(normalized) != len(set(normalized)):
        raise ValueError("exact duplicate combined_text generated")


def _label_distribution(records: list[BenchmarkRecord]) -> dict[str, object]:
    return {
        "events": dict(sorted(Counter(record.event_label.value for record in records).items())),
        "sentiments": dict(
            sorted(Counter(record.sentiment_label.value for record in records).items())
        ),
        "event_sentiment": dict(
            sorted(
                Counter(
                    f"{record.event_label.value}:{record.sentiment_label.value}"
                    for record in records
                ).items()
            )
        ),
        "language": dict(sorted(Counter(record.language for record in records).items())),
        "split": dict(sorted(Counter(record.split for record in records).items())),
        "challenge_records": sum(1 for record in records if record.challenge_flags),
        "challenge_by_split": dict(
            sorted(Counter(record.split for record in records if record.challenge_flags).items())
        ),
        "challenge_flags": dict(
            sorted(Counter(flag for record in records for flag in record.challenge_flags).items())
        ),
    }


def _generation_config() -> dict[str, object]:
    return {
        "dataset_id": DATASET_ID,
        "dataset_version": DATASET_VERSION,
        "generator_version": GENERATOR_VERSION,
        "seed": 20260622,
        "event_label_count": len(EVENTS),
        "sentiment_label_count": len(SENTIMENTS),
        "template_family_count": len(SPLIT_BY_FAMILY),
        "paraphrases_per_story": 3,
        "split_by_family": SPLIT_BY_FAMILY,
        "language_by_family": LANGUAGE_BY_FAMILY,
        "challenge_flags": list(CHALLENGE_FLAGS),
        "real_company_denylist_size": len(REAL_COMPANY_DENYLIST),
    }


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _hash_records(records: list[BenchmarkRecord]) -> str:
    payload = "\n".join(record.model_dump_json() for record in records) + "\n"
    return _hash_text(payload)


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
