#!/usr/bin/env python3
"""
Deterministic validators for the constraint-audited CAPTCHA pilot.

This code intentionally focuses on challenge generation + validation (defensive evaluation),
and does NOT include solver automation or prompt optimization logic.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Dict, Tuple, Optional, List

VOWELS = set("aeiouAEIOU")

@dataclass
class ValidationResult:
    passed: bool
    error: str
    detail: Optional[str] = None

def _load_json(output: str) -> Tuple[Optional[Any], Optional[ValidationResult]]:
    try:
        obj = json.loads(output)
        return obj, None
    except Exception as e:
        return None, ValidationResult(False, "INVALID_JSON", str(e))

def _ensure_obj(obj: Any) -> Optional[ValidationResult]:
    if not isinstance(obj, dict):
        return ValidationResult(False, "INVALID_TYPE", "Expected JSON object")
    return None

def validate_baseline(task: Dict[str, Any], output: str) -> ValidationResult:
    expected = task["answer"]
    # For baseline tasks, we enforce exact match after stripping trailing newlines.
    got = output.rstrip("\n")
    if got == expected:
        return ValidationResult(True, "PASS")
    return ValidationResult(False, "WRONG_ANSWER", f"Expected {expected!r}, got {got!r}")

def validate_constraint(task: Dict[str, Any], output: str) -> ValidationResult:
    v = task["validator"]
    kind = v["kind"]

    # Some validators operate on raw output
    if kind == "raw_exact_no_spaces":
        raw = output.rstrip("\n")
        if " " in raw:
            return ValidationResult(False, "HAS_SPACES")
        if raw == v["exact"]:
            return ValidationResult(True, "PASS")
        return ValidationResult(False, "MISMATCH", f"Expected exact {v['exact']!r}, got {raw!r}")

    # JSON-based validators
    obj, err = _load_json(output)
    if err:
        return err
    err2 = _ensure_obj(obj)
    if err2:
        return err2
    assert isinstance(obj, dict)

    if kind == "json_exact":
        required_keys = set(v["required_keys"])
        if not required_keys.issubset(obj.keys()):
            return ValidationResult(False, "MISSING_KEYS", f"Missing: {sorted(required_keys - set(obj.keys()))}")
        if v.get("no_extra_keys", False):
            extra = set(obj.keys()) - required_keys
            if extra:
                return ValidationResult(False, "EXTRA_KEYS", f"Extra: {sorted(extra)}")
        equals = v.get("equals", {})
        for k, expected in equals.items():
            if obj.get(k) != expected:
                return ValidationResult(False, "CONSTRAINT_VIOLATION", f"{k} expected {expected!r}, got {obj.get(k)!r}")
        return ValidationResult(True, "PASS")

    if kind == "json_words_list":
        key = v["key"]
        if key not in obj:
            return ValidationResult(False, "MISSING_KEYS", f"Missing key: {key}")
        words = obj[key]
        if not isinstance(words, list):
            return ValidationResult(False, "INVALID_TYPE", f"{key} must be a list")
        if len(words) != v["list_len"]:
            return ValidationResult(False, "COUNT_MISMATCH", f"Expected {v['list_len']} words, got {len(words)}")
        for w in words:
            if not isinstance(w, str):
                return ValidationResult(False, "INVALID_TYPE", "All words must be strings")
            if len(w) != v["word_len"]:
                return ValidationResult(False, "CONSTRAINT_VIOLATION", f"Word {w!r} length {len(w)} != {v['word_len']}")
        return ValidationResult(True, "PASS")

    if kind == "json_string_forbidden_chars":
        key = v["key"]
        if key not in obj:
            return ValidationResult(False, "MISSING_KEYS", f"Missing key: {key}")
        s = obj[key]
        if not isinstance(s, str):
            return ValidationResult(False, "INVALID_TYPE", f"{key} must be a string")
        forbidden = v.get("forbidden_chars", [])
        for ch in forbidden:
            if ch in s:
                return ValidationResult(False, "FORBIDDEN_TOKEN", f"Found forbidden char {ch!r}")
        return ValidationResult(True, "PASS")

    if kind == "json_crossfield_charcount":
        text_key = v["text_key"]
        count_key = v["count_key"]
        if text_key not in obj or count_key not in obj:
            return ValidationResult(False, "MISSING_KEYS", f"Need keys: {text_key}, {count_key}")
        text = obj[text_key]
        count = obj[count_key]
        if not isinstance(text, str) or not isinstance(count, int):
            return ValidationResult(False, "INVALID_TYPE", "text must be string; count must be int")
        true_count = len(text)
        if count != true_count:
            return ValidationResult(False, "COUNT_MISMATCH", f"count={count} but len(text)={true_count}")
        return ValidationResult(True, "PASS")

    if kind == "json_list_exact":
        key = v["key"]
        if key not in obj:
            return ValidationResult(False, "MISSING_KEYS", f"Missing key: {key}")
        items = obj[key]
        if items != v["exact"]:
            return ValidationResult(False, "MISMATCH", f"Expected {v['exact']!r}, got {items!r}")
        return ValidationResult(True, "PASS")

    if kind == "json_vowel_count":
        x_key = v["x_key"]
        y_key = v["y_key"]
        if x_key not in obj or y_key not in obj:
            return ValidationResult(False, "MISSING_KEYS", f"Need keys: {x_key}, {y_key}")
        x = obj[x_key]
        y = obj[y_key]
        if not isinstance(x, str) or not isinstance(y, int):
            return ValidationResult(False, "INVALID_TYPE", "x must be string; y must be int")
        if len(x) != v["len"]:
            return ValidationResult(False, "CONSTRAINT_VIOLATION", f"x length {len(x)} != {v['len']}")
        if "regex" in v and not re.match(v["regex"], x):
            return ValidationResult(False, "CONSTRAINT_VIOLATION", "x fails regex")
        true_y = sum(1 for ch in x if ch in VOWELS)
        if y != true_y:
            return ValidationResult(False, "COUNT_MISMATCH", f"y={y} but vowel_count(x)={true_y}")
        return ValidationResult(True, "PASS")

    if kind == "json_enum":
        key = v["key"]
        if key not in obj:
            return ValidationResult(False, "MISSING_KEYS", f"Missing key: {key}")
        val = obj[key]
        if not isinstance(val, str):
            return ValidationResult(False, "INVALID_TYPE", f"{key} must be a string")
        if val not in v["allowed"]:
            return ValidationResult(False, "CONSTRAINT_VIOLATION", f"{val!r} not in allowed {v['allowed']}")
        # Optional: prevent extra keys if only one key intended
        if len(obj.keys()) != 1:
            return ValidationResult(False, "EXTRA_KEYS", "Only 'color' key is allowed")
        return ValidationResult(True, "PASS")

    if kind == "json_digit_sum":
        id_key = v["id_key"]
        sum_key = v["sum_key"]
        if id_key not in obj or sum_key not in obj:
            return ValidationResult(False, "MISSING_KEYS", f"Need keys: {id_key}, {sum_key}")
        s = obj[id_key]
        total = obj[sum_key]
        if not isinstance(s, str) or not isinstance(total, int):
            return ValidationResult(False, "INVALID_TYPE", "id must be string; sum must be int")
        if not re.fullmatch(r"\d{" + str(v["digits"]) + r"}", s):
            return ValidationResult(False, "CONSTRAINT_VIOLATION", f"id must be exactly {v['digits']} digits")
        true_total = sum(int(ch) for ch in s)
        if total != true_total:
            return ValidationResult(False, "COUNT_MISMATCH", f"sum={total} but digit_sum(id)={true_total}")
        return ValidationResult(True, "PASS")

    if kind == "json_unique_letters":
        letters_key = v["letters_key"]
        unique_key = v["unique_key"]
        if letters_key not in obj or unique_key not in obj:
            return ValidationResult(False, "MISSING_KEYS", f"Need keys: {letters_key}, {unique_key}")
        letters = obj[letters_key]
        unique = obj[unique_key]
        if not isinstance(letters, str) or not isinstance(unique, bool):
            return ValidationResult(False, "INVALID_TYPE", "letters must be string; unique must be boolean")
        if len(letters) != v["len"]:
            return ValidationResult(False, "CONSTRAINT_VIOLATION", f"letters length {len(letters)} != {v['len']}")
        if "regex" in v and not re.match(v["regex"], letters):
            return ValidationResult(False, "CONSTRAINT_VIOLATION", "letters fails regex")
        true_unique = len(set(letters)) == len(letters)
        if unique != true_unique:
            return ValidationResult(False, "INCONSISTENT_FIELDS", f"unique={unique} but all_unique={true_unique}")
        return ValidationResult(True, "PASS")

    return ValidationResult(False, "UNKNOWN_VALIDATOR", f"Unknown kind: {kind}")

def validate(task: Dict[str, Any], output: str) -> ValidationResult:
    t = task.get("type")
    if t == "baseline":
        return validate_baseline(task, output)
    if t == "constraint":
        return validate_constraint(task, output)
    return ValidationResult(False, "UNKNOWN_TASK_TYPE", f"Unknown task type: {t}")
