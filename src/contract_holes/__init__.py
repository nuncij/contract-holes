"""Evidence-first Solidity vulnerability scanner."""

from .models import Finding, Severity
from .inheritance import InheritanceResolver
from .project import ProjectIndex
from .scanner import Scanner

__all__ = [
    "Finding",
    "InheritanceResolver",
    "ProjectIndex",
    "Scanner",
    "Severity",
]
__version__ = "0.2.0"
