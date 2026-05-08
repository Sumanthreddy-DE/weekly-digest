from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, Iterator, Optional

from discovery.checkpoint import Checkpoint, read_checkpoint, write_checkpoint
from discovery.models import Company


@dataclass
class SourceRunResult:
    items_emitted: int
    status: str
    error: Optional[str] = None


class SourceBase(ABC):
    name = ""
    geo_tier = "GLOBAL"
    extractor = "custom"

    def __init__(self, config: dict):
        self.config = config
        self.checkpoint_dir = config["discovery"]["checkpoint_dir"]
        self.delay_seconds = config["discovery"]["rss_delay_seconds"]

    @abstractmethod
    def iter_pages(self, start_page: int) -> Iterator[tuple[int, str | None, list[Company]]]:
        pass

    def run(self) -> Iterable[Company]:
        checkpoint = read_checkpoint(self.checkpoint_dir, self.name)
        if checkpoint and checkpoint.status == "completed":
            self.last_run_result = SourceRunResult(
                items_emitted=checkpoint.items_emitted,
                status="completed",
                error=checkpoint.error,
            )
            return []

        start_page = checkpoint.last_completed_page + 1 if checkpoint and checkpoint.status in {"in_progress", "failed"} else 1
        started_at = checkpoint.started_at if checkpoint else _utc_now()
        items_emitted = checkpoint.items_emitted if checkpoint else 0
        yielded: list[Company] = []
        last_page = start_page - 1
        last_url = checkpoint.last_completed_url if checkpoint else None

        try:
            for page_num, page_url, companies in self.iter_pages(start_page):
                last_page = page_num
                last_url = page_url
                items_emitted += len(companies)
                write_checkpoint(
                    self.checkpoint_dir,
                    Checkpoint(
                        source=self.name,
                        started_at=started_at,
                        last_completed_page=page_num,
                        last_completed_url=page_url,
                        items_emitted=items_emitted,
                        status="in_progress",
                    ),
                )
                yielded.extend(companies)
            write_checkpoint(
                self.checkpoint_dir,
                Checkpoint(
                    source=self.name,
                    started_at=started_at,
                    last_completed_page=last_page,
                    last_completed_url=last_url,
                    items_emitted=items_emitted,
                    status="completed",
                ),
            )
            self.last_run_result = SourceRunResult(items_emitted=items_emitted, status="completed")
            return yielded
        except Exception as exc:
            write_checkpoint(
                self.checkpoint_dir,
                Checkpoint(
                    source=self.name,
                    started_at=started_at,
                    last_completed_page=last_page,
                    last_completed_url=last_url,
                    items_emitted=items_emitted,
                    status="failed",
                    error=str(exc),
                ),
            )
            self.last_run_result = SourceRunResult(items_emitted=items_emitted, status="failed", error=str(exc))
            raise


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
