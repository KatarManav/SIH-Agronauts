from collections.abc import Iterable

from app.ingestion.adapters import SourceAdapter
from app.schemas.satellite import SatelliteObservationCreate


class SatelliteReplayAdapter(SourceAdapter):
    """Replay explicitly labeled satellite evidence for demos and development."""

    def __init__(self, observations: Iterable[SatelliteObservationCreate]):
        self._observations = observations

    def fetch(self) -> Iterable[SatelliteObservationCreate]:
        return self._observations
