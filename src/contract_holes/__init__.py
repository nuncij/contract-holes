"""Evidence-first Solidity vulnerability scanner."""

from .models import Finding, Severity
from .authorization import AuthorizationAnalysis
from .callgraph import CallGraph
from .dataflow import DataFlowAnalysis
from .inheritance import InheritanceResolver
from .project import ProjectIndex
from .proxy import ProxyAnalysis
from .reentrancy import ReentrancyAnalysis
from .scanner import Scanner
from .signature import SignatureAnalysis
from .target_taint import CallTargetAnalysis

__all__ = [
    "Finding",
    "AuthorizationAnalysis",
    "CallGraph",
    "CallTargetAnalysis",
    "DataFlowAnalysis",
    "InheritanceResolver",
    "ProjectIndex",
    "ProxyAnalysis",
    "ReentrancyAnalysis",
    "Scanner",
    "Severity",
    "SignatureAnalysis",
]
__version__ = "0.3.0"
