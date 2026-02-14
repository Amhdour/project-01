from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from typing import Any

from trust_layer.events import TrustContext
from trust_layer.events import TrustEvent


class TrustLayer(ABC):
    """Host-agnostic trust hook interface.

    Implementations can mutate/replace payloads, or encode side effects in payload
    extensions according to host needs.
    """

    @abstractmethod
    def hook(self, event: TrustEvent, ctx: TrustContext, payload: Any) -> Any:
        """Process a trust event and return the resulting payload."""
        raise NotImplementedError
