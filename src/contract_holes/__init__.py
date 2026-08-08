"""Evidence-first Solidity vulnerability scanner."""

from .models import Finding, Severity
from .authorization import AuthorizationAnalysis
from .callgraph import CallGraph
from .dataflow import DataFlowAnalysis
from .inheritance import InheritanceResolver
from .project import ProjectIndex
from .reentrancy import ReentrancyAnalysis
from .scanner import Scanner
from .target_taint import CallTargetAnalysis

__all__ = [
    "Finding",
    "AuthorizationAnalysis",
    "CallGraph",
    "CallTargetAnalysis",
    "DataFlowAnalysis",
    "InheritanceResolver",
    "ProjectIndex",
    "ReentrancyAnalysis",
    "Scanner",
    "Severity",
]
__version__ = "0.3.0"
