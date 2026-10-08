"""camelcase — a night-shift camel for your repo."""
from .case import to_camel, to_pascal, to_snake
from .oasis import GaveUp, retry

__version__ = "0.1.0"
__all__ = ["to_camel", "to_pascal", "to_snake", "retry", "GaveUp", "__version__"]
