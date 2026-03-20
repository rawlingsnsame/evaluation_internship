import os
import json
import logging
import textwrap
import time
from dataclasses import dataclass, field
from typing import Dict, List

from openai import OpenAI, APIConnectionError, APIStatusError, APITimeoutError
from dotenv import load_dotenv

from criterions import SCHOOL_CRITERIONS

class ValidationError(Exception):
    """Input data failed validation before reaching the AI."""

class AIResponseError(Exception):
    """All models exhausted or returned unusable responses."""

class InputValidator:
    @staticmethod
    def validate(school: str, personal: dict, performance: dict, remarks: dict) -> None:
        if school not in SCHOOL_CRITERIONS:
            raise ValidationError(
                f"Unknown school '{school}'. Must be one of: {list(SCHOOL_CRITERIONS)}"
            )

        for f in ("name", "id"):
            if not str(personal.get(f, "")).strip():
                raise ValidationError(f"personal['{f}'] is required and cannot be empty.")

        required_perf = ("tasks_done", "tasks_total", "days_present", "total_days", "average_mark")
        for f in required_perf:
            if f not in performance:
                raise ValidationError(f"performance['{f}'] is missing.")
            if not isinstance(performance[f], (int, float)):
                raise ValidationError(
                    f"performance['{f}'] must be a number, got {type(performance[f]).__name__}."
                )

        if performance["tasks_total"] <= 0:
            raise ValidationError("performance['tasks_total'] must be > 0.")
        if not (0 <= performance["tasks_done"] <= performance["tasks_total"]):
            raise ValidationError(
                f"tasks_done ({performance['tasks_done']}) must be between 0 "
                f"and tasks_total ({performance['tasks_total']})."
            )
        if performance["total_days"] <= 0:
            raise ValidationError("performance['total_days'] must be > 0.")
        if not (0 <= performance["days_present"] <= performance["total_days"]):
            raise ValidationError(
                f"days_present ({performance['days_present']}) must be between 0 "
                f"and total_days ({performance['total_days']})."
            )
        if not (0 <= performance["average_mark"] <= 100):
            raise ValidationError(
                f"average_mark ({performance['average_mark']}) must be between 0 and 100."
            )

        if school == "COLTECH":
            if not isinstance(remarks.get("supervisor_remark"), str) or not remarks["supervisor_remark"].strip():
                raise ValidationError("remarks['supervisor_remark'] must be a non-empty string.")
            if not isinstance(remarks.get("comments"), dict) or not remarks["comments"]:
                raise ValidationError("remarks['comments'] must be a non-empty dict.")
            expected = {cid for cid, _, _ in SCHOOL_CRITERIONS["COLTECH"]["definitions"]}
            missing  = expected - remarks["comments"].keys()
            if missing:
                raise ValidationError(f"remarks['comments'] is missing keys: {missing}")
            for k, v in remarks["comments"].items():
                if not isinstance(v, str) or not v.strip():
                    raise ValidationError(f"remarks['comments']['{k}'] must be a non-empty string.")
        else:
            if not isinstance(remarks.get("supervisor_remark"), str) or not remarks["supervisor_remark"].strip():
                raise ValidationError("remarks['supervisor_remark'] must be a non-empty string.")


class ResponseValidator:
    @staticmethod
    def validate(school: str, data: dict) -> None:
        if not isinstance(data.get("summary"), str) or not data["summary"].strip():
            raise AIResponseError("Response missing valid 'summary'.")

        if school == "COLTECH":
            if not isinstance(data.get("criteria"), dict):
                raise AIResponseError("Response missing 'criteria' dict.")
            expected = {cid for cid, _, _ in SCHOOL_CRITERIONS["COLTECH"]["definitions"]}
            missing  = expected - data["criteria"].keys()
            if missing:
                raise AIResponseError(f"Response missing criteria keys: {missing}")
            for cid, entry in data["criteria"].items():
                try:
                    float(entry["score"])
                except (KeyError, TypeError, ValueError):
                    raise AIResponseError(f"Criterion '{cid}' has invalid score: {entry.get('score')!r}")

        elif school == "NAHPI":
            if not isinstance(data.get("items"), dict):
                raise AIResponseError("Response missing 'items' dict.")
            expected = {
                iid
                for s in SCHOOL_CRITERIONS["NAHPI"]["sections"]
                for iid, _ in s["items"]
            }
            missing = expected - data["items"].keys()
            if missing:
                raise AIResponseError(f"Response missing item keys: {missing}")
            for iid, entry in data["items"].items():
                try:
                    score = float(entry["score"])
                except (KeyError, TypeError, ValueError):
                    raise AIResponseError(f"Item '{iid}' has invalid score: {entry.get('score')!r}")
                if not (1 <= score <= 5):
                    raise AIResponseError(f"Item '{iid}' score {score} is out of range 1–5.")
