"""Evidence-first Solidity vulnerability scanner."""

from .models import Finding, Severity
from .authorization import AuthorizationAnalysis
from .callgraph import CallGraph
from .dataflow import DataFlowAnalysis
from .inheritance import InheritanceResolver
from .market import MarketAnalysis
from .project import ProjectIndex
from .proxy import ProxyAnalysis
from .reentrancy import ReentrancyAnalysis
from .scanner import Scanner
from .signature import SignatureAnalysis
from .target_taint import CallTargetAnalysis
from .token import TokenAnalysis

__all__ = [
    "Finding",
    "AuthorizationAnalysis",
    "CallGraph",
    "CallTargetAnalysis",
    "DataFlowAnalysis",
    "InheritanceResolver",
    "MarketAnalysis",
    "ProjectIndex",
    "ProxyAnalysis",
    "ReentrancyAnalysis",
    "Scanner",
    "Severity",
    "SignatureAnalysis",
    "TokenAnalysis",
]
__version__ = "1.1.1"
