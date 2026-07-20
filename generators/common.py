"""Deterministic RNG + small helpers. All randomness in the project funnels
through here so a single SEED reproduces the entire dataset."""
from __future__ import annotations

import numpy as np

import config


def make_rng(stream: int = 0) -> np.random.Generator:
    """Return an independent, reproducible RNG.

    Use distinct `stream` ints for distinct generators so adding a new generator
    never perturbs the output of existing ones (which would break ground truth).
    """
    return np.random.default_rng(config.SEED + stream)


def triangular(rng: np.random.Generator, lo: float, mode: float, hi: float, n: int) -> np.ndarray:
    """Triangular draw — cheap stand-in for a skewed order-value distribution."""
    return rng.triangular(lo, mode, hi, size=n)


def random_dates(rng: np.random.Generator, start: str, end: str, n: int) -> np.ndarray:
    """Uniform random dates in [start, end] as numpy datetime64[D]."""
    s = np.datetime64(start)
    e = np.datetime64(end)
    span = (e - s).astype(int)
    offsets = rng.integers(0, span + 1, size=n)
    return s + offsets.astype("timedelta64[D]")
