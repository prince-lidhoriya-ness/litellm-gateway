"""Per-request deadline shared by every stage that runs a model.

Why this exists: the hook waits for the pipeline with asyncio.wait_for, but a worker thread cannot be cancelled. Before
this module, a timed-out pipeline kept running in the background and kept holding the single compressor lock, so the
next request also timed out (PROJECT_AUDIT_REPORT.md, F-02). Now the pipeline checks the deadline before each model call
and waits for a model lock only as long as the deadline allows. Work that runs past its deadline stops at the next
check instead of running to the end.

The deadline travels in a context variable, so the detector and the compressor can read it without every call site
passing it along. asyncio and the hook's executor copy the context into the worker thread.
"""

import contextvars
import threading
import time
from contextlib import contextmanager
from typing import Iterator, Optional


class DeadlineExceeded(TimeoutError):
    """The request's pipeline deadline passed (or a model lock could not be had before it)."""


class Deadline:
    def __init__(self, seconds: Optional[float] = None):
        self.at = time.monotonic() + seconds if seconds is not None and seconds > 0 else None

    def remaining(self) -> Optional[float]:
        """Seconds left, or None when there is no deadline."""
        return None if self.at is None else max(0.0, self.at - time.monotonic())

    def expired(self) -> bool:
        return self.at is not None and time.monotonic() >= self.at

    def check(self, stage: str) -> None:
        if self.expired():
            raise DeadlineExceeded(f"deadline passed before {stage}")


NO_DEADLINE = Deadline(None)
_current: contextvars.ContextVar = contextvars.ContextVar("prompt_compression_deadline", default=NO_DEADLINE)


def current() -> Deadline:
    return _current.get()


@contextmanager
def use(deadline: Optional[Deadline]) -> Iterator[Deadline]:
    token = _current.set(deadline or NO_DEADLINE)
    try:
        yield _current.get()
    finally:
        _current.reset(token)


@contextmanager
def acquire(lock: threading.Lock, stage: str) -> Iterator[None]:
    """Hold `lock`, waiting at most until the current deadline; DeadlineExceeded if it cannot be had in time."""
    remaining = current().remaining()
    if not lock.acquire(timeout=-1 if remaining is None else remaining):
        raise DeadlineExceeded(f"{stage} busy until the deadline")
    try:
        yield
    finally:
        lock.release()
