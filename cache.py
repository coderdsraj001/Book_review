import logging
import json

# Set up logging
logger = logging.getLogger(__name__)

class MockRedis:
    def __init__(self):
        self.cache = {}

    def get(self, key):
        try:
            return self.cache.get(key)
        except Exception as e:
            logger.error(f"Cache get error: {str(e)}")
            return None

    def set(self, key, value, ex=None):
        try:
            self.cache[key] = value
            return True
        except Exception as e:
            logger.error(f"Cache set error: {str(e)}")
            return False