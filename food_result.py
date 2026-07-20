from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ProcessResult:
    success: bool
    duplicate: bool
    text: str
