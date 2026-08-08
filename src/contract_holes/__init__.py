"""Evidence-first Solidity vulnerability scanner."""

from .models import Finding, Severity
from .callgraph import CallGraph
from .dataflow import DataFlowAnalysis
from .inheritance import InheritanceResolver
from .project import ProjectIndex
from .reentrancy import ReentrancyAnalysis
from .scanner import Scanner

__all__ = [
    "Finding",
    "CallGraph",
    "DataFlowAnalysis",
    "InheritanceResolver",
    "ProjectIndex",
    "ReentrancyAnalysis",
    "Scanner",
    "Severity",
]
__version__ = "0.3.0"
