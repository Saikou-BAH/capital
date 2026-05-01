"""Runtime helpers for local/admin vs production read-only mode."""

from __future__ import annotations

import os

import streamlit as st


def is_read_only_mode() -> bool:
    """Return True when the deployed app must not mutate CSV data."""
    read_only = os.getenv("READ_ONLY", "").strip().lower()
    app_mode = os.getenv("APP_MODE", "").strip().lower()
    return read_only in {"1", "true", "yes", "oui"} or app_mode in {"prod", "production", "readonly"}


def read_only_notice(scope: str = "Cette section") -> None:
    st.info(
        f"{scope} est en lecture seule sur la version déployée. "
        "Modifiez les fichiers CSV en local puis poussez les changements sur GitHub.",
        icon="🔒",
    )
