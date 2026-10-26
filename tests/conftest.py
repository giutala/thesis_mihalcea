"""Shared test setup: render figures without a display."""

from __future__ import annotations

import matplotlib

# Tk is not reliably available on Windows CI or headless shells.
matplotlib.use("Agg")
