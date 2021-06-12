"""
Project-specific constants
"""

__all__ = ['LOG_LEVEL',
           'ERROR_LOG_LEVEL',
           'API_KEY',
           'INTEGRATION_ID']

import os


# Library Log Level
LOG_LEVEL = os.getenv('3PLAY_LOG_LEVEL', 'WARNING').upper()

# Library Log level (for errors)
ERROR_LOG_LEVEL = os.getenv('3PLAY_ERROR_LOG_LEVEL', 'ERROR').upper()

# API Key to use for requests to 3Play API
API_KEY = os.getenv('3PLAY_API_KEY')

# Service Integration ID on 3Play - for example, an integration /w YouTube
INTEGRATION_ID = os.getenv('INTEGRATION_ID')
