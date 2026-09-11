from abc import ABC, abstractmethod
from collections.abc import Iterable

from app.schemas.ingestion import EnvironmentalObservationCreate


class SourceAdapter(ABC):
    """Convert a verified external source into the internal observation contract."""

    @abstractmethod
    def fetch(self) -> Iterable[EnvironmentalObservationCreate]:
        raise NotImplementedError


class DemoReplayAdapter(SourceAdapter):
    """Replay explicitly labeled observations for development and demonstrations."""

    def __init__(self, observations: Iterable[EnvironmentalObservationCreate]):
        self._observations = observations

    def fetch(self) -> Iterable[EnvironmentalObservationCreate]:
        return self._observations
