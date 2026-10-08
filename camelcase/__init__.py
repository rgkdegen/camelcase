"""camelcase: a camel who walks your repo at night."""

from .case import to_camel, to_pascal, to_snake
from .oasis import GaveUp, retry

__version__ = "0.2.0"
__all__ = ["GaveUp", "__version__", "retry", "to_camel", "to_pascal", "to_snake"]
