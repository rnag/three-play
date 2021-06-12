"""
A Python library for the 3Play API v3

Usage:

>>> from three_play.v3 import *
>>> from three_play.v3.models import *
>>>
>>> file_data = ThreePlayApi.list_media_files(name_partial='Testing').get('data', [])
>>> files = [MediaFile(**file) for file in file_data]
>>> print(len(files), files)
>>>
>>> transcripts = ThreePlayHelper.get_transcripts('my-video-id')
>>> print(transcripts)

"""

import logging


__author__ = 'Ritvik Nag'
__email__ = 'rv.kvetch@gmail.com'
__version__ = '0.1.0'


# Set up logging to ``/dev/null`` like a library is supposed to.
# http://docs.python.org/3.3/howto/logging.html#configuring-logging-for-a-library
class NullHandler(logging.Handler):
    def emit(self, record):
        pass


logging.getLogger('three_play').addHandler(NullHandler())
