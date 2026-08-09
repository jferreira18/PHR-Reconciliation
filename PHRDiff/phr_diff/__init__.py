"""GCSS-Army Primary Hand Receipt semantic and visual diffing."""

from .compare import compare_receipts
from .parser import parse_hand_receipt

__all__ = ["compare_receipts", "parse_hand_receipt"]

