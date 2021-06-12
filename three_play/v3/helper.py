"""
Utility functions for interacting with the 3Play API.
"""
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Union, Tuple, Type

from .api import ThreePlayApi
from .models.three_play_media import *
from ..errors import *
from ..log import LOG
from ..utils.parse import (total_ms, remove_dialogue_between,
                           remove_dialogue_for_first_ts)


class ThreePlayHelper:
    """
    Helper class for interacting with 3Play API, which further simplifies
    any calls. This assumes that :class:`ThreePlayApi` has been configured
    as needed with the API token.

    """

    @staticmethod
    def as_turnaround(turnaround_name: str,
                      default: Union[Turnaround, TurnaroundAD] = None,
                      cls: Type[Union[Turnaround, TurnaroundAD]] = Turnaround):
        """
        Attempt to parse a string as a :class:`Turnaround` or :class:`TurnaroundAD`.

        If `turnaround_name` is not provided, return the `default` value. Otherwise
        if `turnaround_name` is invalid, an :class:`ThreePlayError` is raised.
        """
        if turnaround_name:
            try:
                turnaround = cls[turnaround_name.upper().replace(' ', '_')]
                return turnaround
            except KeyError:
                raise InvalidTurnaround(turnaround_name)

        return default

    @staticmethod
    def get_transcript_language(video_id, transcripts=None) -> Language:
        """
        When 'source_language' is not passed in the request, get the primary
        language for a video spoken in an other language from the existing 3Play
        transcript.

        Raises an ThreePlayError if no record for a transcript exists on 3Play.

        """
        if transcripts is None:
            t = ThreePlayApi.get_transcripts(
                video_id=video_id, sort_by_created=True)
            transcripts = t['data']

        # Iterate over transcripts (most recent first) and find the first media file
        # with a default transcript - this is the transcript we will use to determine the
        # primary or source language.
        for transcript in reversed(transcripts):
            if transcript.get('default') is True:
                media_file_id = transcript['media_file_id']
                transcript_id = transcript['id']
                status = TranscriptStatus(transcript['status'])
                lang_id = transcript['language_id']

                if status is TranscriptStatus.CANCELLED:
                    continue

                LOG.info('Found latest transcript for video. '
                         'file_id=%d, transcript_id=%d', media_file_id, transcript_id)
                try:
                    return Language(int(lang_id))
                except (ValueError, TypeError):
                    raise InvalidLanguageId(lang_id, transcript_id)

        raise NoSuchTranscript(video_id, has_lang_input=True)

    @staticmethod
    def get_transcripts(video_id, status: TranscriptStatus = None,
                        by_default=False, latest_first=False) -> List[Dict]:
        """
        Get all transcripts for a given video.
        """
        t = ThreePlayApi.get_transcripts(
            video_id=video_id, sort_by_created=True,
            status=status, by_default=by_default, latest_first=latest_first)
        transcripts = t['data']

        return transcripts

    @staticmethod
    def get_latest_media_file(video_id: str) -> MediaFile:
        """
        Get the latest media file for a video.
        """
        response = ThreePlayApi.list_media_files(
            video_id=video_id, sort_by_created=True, latest_first=True)

        try:
            mf = MediaFile(**response['data'][0])
        except (IndexError, KeyError):
            raise NoSuchMediaFile(video_id)

        return mf

    @classmethod
    def get_default_transcripts(cls, video_id, status: TranscriptStatus = None,
                                latest_first=False) -> List[Dict]:
        """
        Get default transcripts for a video
        """
        default_transcripts = cls.get_transcripts(
            video_id, status, by_default=True, latest_first=latest_first)

        return default_transcripts

    @staticmethod
    def cancel_transcripts(transcripts: List[Dict] = None, video_id=None):
        """
        Attempt to cancel any in progress or pending transcript orders
        for a given video, or given a list of transcripts for a video.
        """
        if transcripts is None:
            transcripts = ThreePlayHelper.get_transcripts(video_id)

        for transcript in transcripts:
            transcript_id = transcript['id']
            status = TranscriptStatus(transcript['status'])

            if not (status is TranscriptStatus.COMPLETE):
                if status is TranscriptStatus.CANCELLED:
                    continue
                # If transcript is still pending or in progress, attempt to
                # cancel the transcript order, but don't need to check
                # if it was a success.
                LOG.info('Attempting to cancel a %s transcript (%d)',
                         status.value, transcript_id)
                ThreePlayApi.cancel_transcript(transcript_id)

    @staticmethod
    def get_active_transcripts(video_id) -> Dict[int, Language]:
        """
        Returns the most recent transcripts (which includes the original transcript,
        and any translations in the case of videos in another language) for the video
        from 3Play. Returns a dictionary mapping each Transcript Id to Language.

        These transcripts are also the ones we would expect to show up as captions
        on the integration service.

        Raises an ThreePlayError if no transcripts are found, or a source language
        is invalid.

        """
        t = ThreePlayApi.get_transcripts(video_id=video_id, sort_by_created=True,
                                         status=TranscriptStatus.COMPLETE)
        transcripts = t['data']

        # Iterate over transcripts (most recent first) and find the first media file
        # with a default transcript - this is the file we will use for transcripts.
        for transcript in reversed(transcripts):
            if transcript.get('default') is True:
                media_file_id = transcript['media_file_id']
                break
        else:
            raise NoSuchTranscript(video_id)

        file_transcripts = [transcript for transcript in transcripts
                            if transcript['media_file_id'] == media_file_id]

        transcript_id_to_language = {}
        for transcript in file_transcripts:
            transcript_id, lang_id = transcript['id'], transcript['language_id']
            try:
                lang = Language(lang_id)
            except ValueError:
                raise InvalidLanguageId(lang_id, transcript_id)

            transcript_id_to_language[transcript_id] = lang

        return transcript_id_to_language

    @staticmethod
    def get_active_transcript_list(video_id) -> List[Transcript]:
        """
        Returns the most recent transcripts (which includes the original transcript,
        and any translations in the case of videos in another language) for the video
        from 3Play. Returns a list of :class:`Transcript` objects.

        These transcripts are also the ones we would expect to show up as captions
        on the integration service.

        Raises an ThreePlayError if no transcripts are found, or a source language
        is invalid.

        """
        t = ThreePlayApi.get_transcripts(video_id=video_id, sort_by_created=True,
                                         status=TranscriptStatus.COMPLETE)
        transcripts = t['data']

        # Iterate over transcripts (most recent first) and find the first media file
        # with a default transcript - this is the file we will use for transcripts.
        for transcript in reversed(transcripts):
            if transcript.get('default') is True:
                media_file_id = transcript['media_file_id']
                break
        else:
            raise NoSuchTranscript(video_id)

        file_transcripts = [Transcript(media_file=None, **transcript)
                            for transcript in transcripts
                            if transcript['media_file_id'] == media_file_id]

        return file_transcripts

    @staticmethod
    def cut_transcript_in_middle(
        transcript_id: int, first_end: str, second_start: str,
        second_offset_ms: int = 0,
        second_end: str = '99:99:99,999') -> str:
        """
        Get the edited transcript for a `transcript_id` from 3Play after making
        a single cut in the middle. The dialogue between `first_end` and
        `second_start` (non-inclusive of the latter) won't show up in the
        transcript returned.

        This method is needed partly because the `clips[]` argument is not handled
        as expected on the 3Play side, e.g. even without `second_offset_ms`
        added we still seem to get duplicate dialogue for `first_end`.

        """
        first_end_ms = initial_first_end_ms = total_ms(first_end)
        second_start_ms = total_ms(second_start)
        second_end_ms = total_ms(second_end)

        if second_offset_ms:
            # Add the delay for the second segment to the duration on first part
            # We will also need to remove unneeded dialogue later.
            first_end_ms += second_offset_ms

        clips = [f'0,{first_end_ms}', f'{second_start_ms},{second_end_ms}']

        text = ThreePlayApi.get_formatted_transcript_text(transcript_id, clips=clips)

        if second_offset_ms:
            text = remove_dialogue_between(text, initial_first_end_ms, first_end_ms)
        else:
            text = remove_dialogue_for_first_ts(text, first_end)

        return text

    @staticmethod
    def get_both_transcript_text(
        transcript_id: int,
        start_seconds: Union[str, int, float]) -> Tuple[str, str]:
        """
        Retrieve the original transcript text and the trimmed transcript
        text (after adding the offset `start_seconds` to the text)

        :param transcript_id: ID of the 3Play transcript to retrieve the formatted
            text (in SRT format) for
        :param start_seconds: Start offset to specify to trim the transcript
        :return: A tuple of (original_text, trimmed_text)

        """
        with ThreadPoolExecutor(max_workers=2) as pool:
            original_text_future = pool.submit(
                ThreePlayApi.get_formatted_transcript_text, transcript_id)
            trimmed_text_future = pool.submit(
                ThreePlayApi.get_formatted_transcript_text, transcript_id,
                start_seconds=start_seconds)

        original_text = original_text_future.result()
        trimmed_text = trimmed_text_future.result()

        return original_text, trimmed_text
