"""Convert AI-READI files into pandas tables."""
__version__ = "0.2.0"
from .api import load_clinical, load_cgm
from .cgm import CGMConfig

__all__ = ["load_clinical", "load_cgm", "CGMConfig"]
