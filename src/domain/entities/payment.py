# Payment entity is defined in src/domain/entities/invoice.py
# as part of the Invoice aggregate root.
# Re-exported here for convenience.

from src.domain.entities.invoice import Payment

__all__ = ["Payment"]
