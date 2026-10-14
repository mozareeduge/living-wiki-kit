"""Shared test hygiene: close every sqlite connection a test opens.

An open handle keeps `_search/*.db` locked on Windows and shows up as a
ResourceWarning; tests that return a connection from a helper would
otherwise leak it.
"""
from __future__ import annotations

import sqlite3

import pytest


@pytest.fixture(autouse=True)
def _close_sqlite_connections(monkeypatch):
    opened: list[sqlite3.Connection] = []
    real_connect = sqlite3.connect

    def connect(*args, **kwargs):
        con = real_connect(*args, **kwargs)
        opened.append(con)
        return con

    monkeypatch.setattr(sqlite3, "connect", connect)
    yield
    for con in opened:
        con.close()
