from typing import Optional

from ..models import Quote
from .base import Item

QUOTE_STATUS = {
    0: "pending",
    1: "accepted",
    2: "rejected",
    3: "revoked",
    4: "deleted",
}


class QuoteItem(Item):
    state: str
    quoted_status: Optional["StatusItem"] = None

    @classmethod
    def from_model(cls, quote: Quote):
        cls.get_state(quote)
        quoted_status = cls.get_quoted_status(quote)

        return cls(state=QUOTE_STATUS[quote.state], quoted_status=quoted_status)

    @classmethod
    def get_state(
        cls,
        quote: Quote,
    ) -> str:
        if quote.state != 1:  # 1 is 'accepted'
            return QUOTE_STATUS[quote.state]

        if quote.status is None:
            return "deleted"

        # TODO: StatusFilter

        return QUOTE_STATUS[quote.state]

    @classmethod
    def get_quoted_status(cls, quote: Quote) -> Optional["StatusItem"]:
        if quote.state != 1:
            return None

        if quote.status is None:
            return None

        if quote.status.reblog_of_id is not None:
            return None

        # TODO: StatusFilter

        from .status import StatusItem

        return StatusItem.from_model(quote.quoted_status, with_reblog=False)
