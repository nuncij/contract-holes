"""Evidence-first Solidity vulnerability scanner."""

from .models import Finding, Severity
from .callgraph import CallGraph
from .dataflow import DataFlowAnalysis
from .inheritance import InheritanceResolver
from .project import ProjectIndex
from .scanner import Scanner

__all__ = [
    "Finding",
    "CallGraph",
    "DataFlowAnalysis",
    "InheritanceResolver",
    "ProjectIndex",
    "Scanner",
    "Severity",
]
__version__ = "0.2.0"
