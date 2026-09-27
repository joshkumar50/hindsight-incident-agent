"""
=============================================================
shared/__init__.py - Package initializer
=============================================================
"""
# Expose key items at the package level for clean imports
from shared.config import config
from shared.models import (
    AnalysisRequest,
    AnalysisResponse,
    AnalysisStatus,
    RootCauseAnalysis,
    Severity,
)

__all__ = [
    "config",
    "AnalysisRequest",
    "AnalysisResponse",
    "AnalysisStatus",
    "RootCauseAnalysis",
    "Severity",
]
