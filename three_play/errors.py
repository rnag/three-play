"""
Project-specific exception classes
"""
__all__ = ['ThreePlayError',
           'ADIsNotComplete',
           'InvalidSourceLanguage',
           'InvalidLanguageId',
           'InvalidTurnaround',
           'NoSuchMediaFile',
           'NoSuchTranscript']

from .log import LOG
from .utils.response import format_error


class ThreePlayError(Exception):

    ERR_STATUS = 400

    def __init__(self, message, **log_kwargs):
        self.message = message
        self.code = self.__class__.__name__

        super(ThreePlayError, self).__init__(self.message)

        if log_kwargs:
            field_vals = [f'{k}={v}' for k, v in log_kwargs.items()]
            if message[-1] != '.':
                message += '.'

            msg = f'{self.code}: {message} {", ".join(field_vals)}'
        else:
            msg = f'{self.code}: {self.message}'

        LOG.error(msg)

    def response(self):
        """Formats an error object and returns an AWS Lambda Proxy response."""
        return format_error(self.message, self.code, self.ERR_STATUS)


class InvalidLanguageId(ThreePlayError):
    """
    Raised when a 3Play transcript has an invalid / unexpected language id.
    """
    def __init__(self, language_id, transcript_id):
        msg = (f'Invalid language id for transcript '
               f'(language_id={language_id}, transcript_id={transcript_id})')
        super(InvalidLanguageId, self).__init__(msg)


class InvalidSourceLanguage(ThreePlayError):
    """
    Raised when a request contains an invalid source language for placing transcript orders.
    """
    def __init__(self, source_language):
        msg = f'Invalid or missing source language ({source_language})'
        super(InvalidSourceLanguage, self).__init__(msg)


class InvalidTurnaround(ThreePlayError):
    """
    Raised when a request contains an invalid 3Play turnaround level
    """
    def __init__(self, turnaround_name):
        msg = f'{turnaround_name} is not a valid turnaround level'
        super(InvalidTurnaround, self).__init__(msg)


class NoSuchMediaFile(ThreePlayError):
    """
    Raised when a media file does not exist on 3Play for a given video id
    """
    def __init__(self, video_id):
        msg = 'No valid media file exist for the video.'
        super(NoSuchMediaFile, self).__init__(msg, video_id=video_id)


class NoSuchTranscript(ThreePlayError):
    """
    Raised when a completed transcript order does not exist on 3Play for a given video id
    """
    def __init__(self, video_id, has_lang_input=False):
        msg = 'No valid transcripts exist for the video.'
        if has_lang_input:
            msg = f'{msg} Please specify the transcript source language in the request.'

        super(NoSuchTranscript, self).__init__(msg, video_id=video_id)


class ADIsNotComplete(ThreePlayError):
    """
    Raised when an Audio Description order is not complete and still in progress.
    """
    def __init__(self, video_id: str):
        msg = 'The Audio Description is still in progress for the video.'
        super(ADIsNotComplete, self).__init__(msg, video_id=video_id)
