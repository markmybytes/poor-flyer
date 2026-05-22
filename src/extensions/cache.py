"""Cache extension module."""

import logging

from flask_caching import Cache

logger = logging.getLogger(__name__)

cache = Cache(config={'CACHE_TYPE': 'SimpleCache', 'CACHE_DEFAULT_TIMEOUT': 86400})
