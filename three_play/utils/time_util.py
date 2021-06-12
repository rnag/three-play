"""
Time utilities
"""
import sys
import time


# Preferred clock, based on which one is more accurate on a given system.
# Ported from `requests`
if sys.platform == 'win32':
    try:  # Python 3.4+
        preferred_clock = time.perf_counter
    except AttributeError:  # Earlier than Python 3.
        preferred_clock = time.clock
else:
    preferred_clock = time.time
