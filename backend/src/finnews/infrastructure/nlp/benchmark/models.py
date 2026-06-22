from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from finnews.domain.enums import EventType, SentimentLabel

DATASET_ID = "synthetic-finnews-nlp-v1"
DATASET_VERSION = "1.0.0"
GENERATOR_VERSION = "m2a-v1"

Language = Literal["zh", "en"]
Split = Literal["train", "validation", "test"]
Difficulty = Literal["easy", "medium", "hard"]
SourceTypeLabel = Literal["synthetic_wire", "synthetic_exchange_notice", "synthetic_research_note"]

CHALLENGE_FLAGS = (
    "negation",
    "uncertainty",
    "mixed_signal",
    "hypothetical_or_plan",
    "class_overlap",
    "numerical_reversal",
    "cross_sentence_context",
    "short_text",
    "long_text",
    "alias_or_ticker",
    "neutral_boilerplate",
    "low_information",
)


class BenchmarkRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record_id: str = Field(pattern=r"^m2a-[a-z0-9_-]+$")
    dataset_id: str = DATASET_ID
    dataset_version: str = DATASET_VERSION
    language: Language
    title: str = Field(min_length=1, max_length=240)
    summary: str = Field(min_length=1, max_length=900)
    combined_text: str = Field(min_length=1, max_length=1200)
    event_label: EventType
    sentiment_label: SentimentLabel
    company_id: str = Field(pattern=r"^fc-[0-9]{3}$")
    fictional_ticker: str = Field(pattern=r"^F[A-Z0-9]{3}$")
    industry: str = Field(min_length=1, max_length=80)
    source_type: SourceTypeLabel
    published_at: datetime
    template_family_id: str = Field(pattern=r"^tf-[0-9]{2}$")
    story_group_id: str = Field(pattern=r"^sg-[a-z0-9_-]+$")
    paraphrase_id: int = Field(ge=0, le=2)
    split: Split
    difficulty: Difficulty
    challenge_flags: list[str] = Field(default_factory=list)
    label_source: str = "generator_defined_synthetic_gold"
    generator_version: str = GENERATOR_VERSION

    @field_validator("challenge_flags")
    @classmethod
    def validate_challenge_flags(cls, value: list[str]) -> list[str]:
        unknown = set(value) - set(CHALLENGE_FLAGS)
        if unknown:
            raise ValueError(f"unknown challenge flags: {sorted(unknown)}")
        if len(value) != len(set(value)):
            raise ValueError("challenge flags must be unique per record")
        return sorted(value)

    @model_validator(mode="after")
    def validate_combined_text(self) -> BenchmarkRecord:
        expected = f"TITLE: {self.title}\nSUMMARY: {self.summary}"
        if self.combined_text != expected:
            raise ValueError("combined_text must be derived from title and summary")
        return self
