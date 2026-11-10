"""Convert AI-READI clinical measurements into pandas tables."""
__version__ = "0.4.0"
from .api import load_clinical

__all__ = ["load_clinical"]
