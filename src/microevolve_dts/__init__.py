"""MicroEvolve-DTS: local heuristic evolution for Difference Triangle Sets."""

from .model import DTSSpec, VerificationResult
from .verify import verify_rows

__all__ = ["DTSSpec", "VerificationResult", "verify_rows"]
__version__ = "0.1.0"
