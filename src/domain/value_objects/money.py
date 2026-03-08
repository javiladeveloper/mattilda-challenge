from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from src.domain.exceptions import ValidationError


class Money:
    """Immutable value object representing a monetary amount."""

    ZERO: Money

    def __init__(self, amount: Decimal | float | int | str) -> None:
        value = Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if value < 0:
            raise ValidationError("Money amount cannot be negative", field="amount")
        object.__setattr__(self, "_amount", value)

    @property
    def amount(self) -> Decimal:
        return self._amount

    def __add__(self, other: Money) -> Money:
        if not isinstance(other, Money):
            return NotImplemented
        return Money(self._amount + other._amount)

    def __sub__(self, other: Money) -> Money:
        if not isinstance(other, Money):
            return NotImplemented
        result = self._amount - other._amount
        if result < 0:
            raise ValidationError("Subtraction would result in negative money")
        return Money(result)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        return self._amount == other._amount

    def __lt__(self, other: Money) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        return self._amount < other._amount

    def __le__(self, other: Money) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        return self._amount <= other._amount

    def __gt__(self, other: Money) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        return self._amount > other._amount

    def __ge__(self, other: Money) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        return self._amount >= other._amount

    def __hash__(self) -> int:
        return hash(self._amount)

    def __repr__(self) -> str:
        return f"Money({self._amount})"

    def __str__(self) -> str:
        return f"${self._amount:,.2f}"

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("Money is immutable")

    def is_zero(self) -> bool:
        return self._amount == Decimal("0.00")

    def to_decimal(self) -> Decimal:
        return self._amount


Money.ZERO = Money(0)
