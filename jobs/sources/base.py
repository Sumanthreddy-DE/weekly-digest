from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable

from jobs.models import Job


class JobSourceBase(ABC):
    def __init__(self, config: dict):
        self.config = config

    @abstractmethod
    def run(self) -> Iterable[Job]:
        raise NotImplementedError
