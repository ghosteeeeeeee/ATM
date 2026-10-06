#!/usr/bin/env python3
"""Serialize candles.db writers (price_collector vs _aggregate_1m)."""
import fcntl
import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
from paths import CANDLES_LOCK


def acquire(timeout_s=90):
    """Block until the exclusive candles.db writer lock is held. Returns fd."""
    fd = open(CANDLES_LOCK, 'w')
    deadline = time.time() + timeout_s
    while True:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return fd
        except OSError:
            if time.time() >= deadline:
                fd.close()
                raise
            time.sleep(0.25)


def release(fd):
    if fd is None:
        return
    try:
        fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        fd.close()
