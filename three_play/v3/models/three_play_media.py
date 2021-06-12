"""
3Play API models.
"""

__all__ = ['Language',
           'TranslationOption',
           'TranscriptFormat',
           'TranscriptStatus',
           'Turnaround',
           'TurnaroundAD',
           'MediaFile',
           'Transcript',
           'AudioDescription']

import logging
from dataclasses import dataclass
from datetime import datetime

from enum import Enum
from typing import Optional


LOG = logging.getLogger(__name__)


class Language(Enum):
    """
    Language names and IDs used in the 3Play API.
    """
    CHINESE = 18
    ENGLISH = 1
    FRENCH = 5
    GERMAN = 7
    ITALIAN = 8
    SPANISH = 13
    JAPANESE = 23


class TranslationOption(Enum):
    """
    Translation Options used in the 3Play API -- defaults to the vendor
    "Gengo - Standard", which is the cheapest option.
    """

    # Translations from English to other language
    ENGLISH_TO_CHINESE = 56
    ENGLISH_TO_FRENCH = 94
    ENGLISH_TO_GERMAN = 97
    ENGLISH_TO_ITALIAN = 116
    ENGLISH_TO_SPANISH = 93
    ENGLISH_TO_JAPANESE = 76

    # Translations from other language to English
    CHINESE_TO_ENGLISH = 285
    FRENCH_TO_ENGLISH = 290
    GERMAN_TO_ENGLISH = 287
    ITALIAN_TO_ENGLISH = 294
    SPANISH_TO_ENGLISH = 132
    JAPANESE_TO_ENGLISH = 282

    @classmethod
    def get(cls, source_language: Language,
            target_language: Language) -> 'TranslationOption':
        """
        Return the translation option from source to target language.
        """
        name = f'{source_language.name}_TO_{target_language.name}'
        return cls.__members__[name]


class TranscriptFormat(Enum):
    # Note: Make an API call to '/transcripts/output_formats' to get the full
    # list of available output formats for transcripts.
    SRT = 7


class TranscriptStatus(Enum):
    """
    Transcript statuses used in the 3Play API.
    """
    IN_PROGRESS = 'in_progress'
    PENDING = 'pending'
    COMPLETE = 'complete'
    CANCELLED = 'cancelled'

    @property
    def title(self):
        return self.value.replace('_', ' ').title()


class TurnaroundBase(Enum):

    def __new__(cls, id, hours, price_rate_increment):
        obj = object.__new__(cls)
        obj._value_ = obj.id = id
        obj.hours = hours
        obj.price_rate = price_rate_increment
        return obj

    @property
    def title(self):
        return self._name_.replace('_', ' ').title()

    def __repr__(self):
        return (f'<{self.__class__.__name__}.{self._name_}: '
                f'id={self._value_}, hours={self.hours}, price={self.price_rate}>')

    def __str__(self):
        return self.__repr__()

    @classmethod
    def sort_by_hours(cls, reverse=False):
        return sorted(cls.__members__.values(), key=lambda e: e.hours, reverse=reverse)

    @classmethod
    def sort_by_price(cls, reverse=False):
        return sorted(cls.__members__.values(), key=lambda e: e.price_rate, reverse=reverse)


class Turnaround(TurnaroundBase):
    """
    Turnaround levels and IDs used in the 3Play API.
    """
    STANDARD = 1, 96, 0.00
    SAME_DAY = 2, 8, 2.50
    RUSH = 3, 24, 1.50
    EXPEDITED = 4, 48, 0.75
    EXTENDED = 5, 240, -0.20
    TWO_HOUR = 6, 2, 5.50


class TurnaroundAD(TurnaroundBase):
    """
    Turnaround levels and IDs for the Audio Description service.
    """
    STANDARD = 7, 120, 0.00
    EXPEDITED = 8, 48, 2.00
    RUSH = 9, 24, 4.00


@dataclass(init=False)
class MediaFile:
    id: int
    name: str
    duration: int
    language: Language
    source: str
    video_id: str
    created_at: datetime
    updated_at: datetime

    def __init__(self, **kwargs):
        self.id = kwargs['id']
        self.name = kwargs['name']
        self.duration = kwargs['duration']
        self.language = Language(kwargs['language_id'])
        self.source = kwargs['source']
        self.video_id = kwargs['reference_id']
        self.created_at = datetime.fromisoformat(kwargs['created_at'])
        self.updated_at = datetime.fromisoformat(kwargs['updated_at'])

    @staticmethod
    def url(file_id: int) -> str:
        return f'https://account.3playmedia.com/files/{file_id}'


@dataclass(init=False)
class Transcript:
    id: str
    media_file_id: int
    video_id: str
    duration: int
    default: bool
    type: str
    language: Language
    status: TranscriptStatus
    cancellable: bool

    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    transcript_types = {'TranslatedTranscript': 'Translation',
                        'TranscribedTranscript': 'Transcript',
                        'ReviewedTranscript': 'Transcript (Reviewed)',
                        'ImportedTranscript': 'Transcript (Imported)',
                        'VendorTranscribedTranscript': 'Transcript (Vendor)',
                        'AsrTranscript': 'ASR'}

    def __init__(self, media_file: MediaFile = None, **kwargs):
        self.id = str(kwargs['id'])
        self.media_file_id = kwargs['media_file_id']
        self.video_id = kwargs['reference_id']
        self.duration = kwargs['duration'] or 0
        self.default = kwargs['default']
        self.type = self.transcript_types.get(
            kwargs['type'], kwargs['type'])
        self.language = Language(kwargs['language_id'])
        self.status = TranscriptStatus(kwargs['status'])
        self.cancellable = kwargs['cancellable']

        if media_file:
            self.created_at = media_file.created_at
            if self.status is TranscriptStatus.COMPLETE:
                self.completed_at = media_file.updated_at


@dataclass(init=False)
class AudioDescription:
    id: str
    media_file_id: int
    video_id: str
    duration: int
    language: Language
    status: TranscriptStatus
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    type: str = 'Audio Description'

    def __init__(self, media_file: MediaFile = None, **kwargs):
        # Use a different id for the audio descriptions, since we don't know
        # if they would clash with the transcript id's
        self.id = f'ad-{kwargs["id"]}'

        self.media_file_id = kwargs['media_file_id']
        self.video_id = kwargs['reference_id']
        self.duration = kwargs['duration']
        self.language = Language.ENGLISH
        self.status = TranscriptStatus(kwargs['status'])

        if media_file:
            self.language = media_file.language
            self.created_at = media_file.updated_at
            if self.status is TranscriptStatus.COMPLETE:
                self.completed_at = media_file.updated_at

    @property
    def raw_id(self) -> str:
        """Returns the 3Play Id for the Audio Description file"""
        return self.id[3:]

    def asset_url(self, dl_format='mp3'):
        url = f'https://account.3playmedia.com/audio_descriptions/{self.raw_id}/' \
              f'download_asset?download_format={dl_format}'

        return url

    @staticmethod
    def is_available(lang: Language):
        """
        Check if Audio Description is available for a language.

        Currently, 3Play only offers AD for videos in English and Spanish.
        """
        return lang in (Language.ENGLISH, Language.SPANISH)
