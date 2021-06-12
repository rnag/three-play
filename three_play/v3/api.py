import json
import logging
import math
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import timedelta, datetime
from logging import INFO, ERROR
from typing import List, Union, Optional, Dict, Any

from requests.exceptions import HTTPError, ConnectionError, RequestException
from requests.models import Response
from requests.packages.urllib3 import Timeout
from requests.sessions import Session

from .models.requests import SessionWithRetry
from .models.three_play_media import *
from .models.three_play_media import TranslationOption
from ..constants import *
from ..errors import ADIsNotComplete
from ..log import get_file_logger, LOG
from ..utils.time_util import preferred_clock


LOG_FILENAME = os.getenv('LOG_FILE', '3play_requests.log')
API_ERROR_LOG_LVL: int = logging._nameToLevel.get(ERROR_LOG_LEVEL, ERROR)

if os.getenv('AWS_LAMBDA_FUNCTION_NAME'):   # Running on Lambda
    pass
else:
    LOG = get_file_logger(filename=LOG_FILENAME, name=__file__, level=LOG_LEVEL)


class ThreePlayApi:
    """
    Helper class to make requests to the 3Play Media API
    """

    API_ENDPOINT = 'https://api.3playmedia.com/v3/'

    # Configure using the env variable by default
    __API_KEY = API_KEY

    @classmethod
    def configure(cls, project_api_key):
        cls.__API_KEY = project_api_key

    @classmethod
    def _get_session(cls) -> Session:
        session = SessionWithRetry()
        session.params = {'api_key': cls.__API_KEY}

        return session

    @classmethod
    def get(cls, api, **kwargs):
        return cls.request('GET', api, **kwargs)

    @classmethod
    def request(cls, method, api, log_level=INFO, **kwargs):
        response = cls._request_page(method, api, log_level=log_level, **kwargs)

        if 'pagination' in response:
            per_page = response['pagination']['per_page']
            total_entries = response['pagination']['total_entries']

            num_pages = math.ceil(total_entries / per_page)
            if num_pages > 1:

                # Need if the pages are expected to contain sorted results
                page_to_data = {}

                with ThreadPoolExecutor(max_workers=5) as pool:
                    future_to_page = {pool.submit(cls._request_page,
                                                  method, api, page, log_level, **kwargs): page
                                      for page in range(2, num_pages + 1)}

                    for future in as_completed(future_to_page):
                        page = future_to_page[future]

                        try:
                            page_data = future.result().get('data') or []

                        except Exception as e:
                            LOG.log(API_ERROR_LOG_LVL,
                                    'Page %d generated an exception: (%s) %s',
                                    page, type(e).__name__, e)

                        else:
                            page_to_data[page] = page_data

                for _, page_data in sorted(page_to_data.items()):
                    response['data'].extend(page_data)

        return response

    @classmethod
    def _request_page(cls, method, api, page=None, log_level=INFO,
                      **kwargs) -> Dict[str, Any]:
        """
        Makes an HTTP request to the 3Play API, or requests a single page
        in the case of a GET request.

        Raises an :class:`HTTPError` for any 4xx or 5xx errors, or a
        :class:`ConnectionError` for any request timeouts or connection
        errors.

        """
        url = cls.API_ENDPOINT + api.lstrip('/')
        params = (kwargs.pop('params', None) or {}).copy()
        if page:
            params['page'] = page

        start = preferred_clock()

        try:
            r = cls._get_session().request(method, url, params=params, **kwargs)

        except ConnectionError as e:
            # Request timed out, or a connection error occurred.
            cls._handle_response(method, api, params, start=start, error=e)

        else:
            # A response was received, check status code and raise any errors.
            cls._handle_response(method, api, params, r, log_level=log_level)
            return r.json()

    @staticmethod
    def _handle_response(
            method: str, api: str, params: Optional[Dict] = None,
            r: Optional[Response] = None, start: Optional[float] = 0.0,
            error: Optional[RequestException] = None,
            log_level=INFO):
        """
        Process and log the :class:`Response` returned for a request

        Requires either `r` or `error` to be passed in to the method
        """
        method = method.upper()
        params = (params or {}).copy()

        # Remove 'callback' since the API key could be in the url, and we don't want to log it
        params.pop('callback', None)

        if r is not None:
            # An HTTP response was received.
            try:
                r.raise_for_status()
            except HTTPError:
                LOG.log(API_ERROR_LOG_LVL,
                        '[%s] %s /%s, params=%s, status=%d, reason=%s, response=%s',
                        r.elapsed, method, api, json.dumps(params),
                        r.status_code, r.reason, r.text)
                raise
            # The request was a success.
            LOG.log(log_level, '[%s] %s /%s, params=%s, status=%d',
                    r.elapsed, method, api, json.dumps(params),
                    r.status_code)

        else:
            # A response was not received, as most likely the request timed out.
            diff_sec = preferred_clock() - start
            elapsed = timedelta(seconds=diff_sec)
            error_code = type(error).__name__

            LOG.warning('[%s] %s /%s, params=%s, error=%s',
                        elapsed, method, api, json.dumps(params), error_code)
            raise error

    @classmethod
    def list_platform_integrations(cls):
        r = cls.get('video_platform_integrations')
        return r

    @classmethod
    def list_turnaround_levels(cls, show_prices=True):
        params = {'prices': str(show_prices).lower()}

        r = cls.get('turnaround_levels', params=params)
        return r

    @classmethod
    def list_languages(cls, lang_id: Union[int, List[int]] = None,
                       name: str = None,
                       name_partial: str = None) -> List[Dict[str, Any]]:
        params = {}
        if lang_id:
            params['id'] = lang_id
        if name:
            params['name'] = name
        if name_partial:
            params['name_cont'] = name_partial

        r = cls.get('languages', params=params)
        return r.get('data') or []

    @classmethod
    def list_translation_options(cls, source_language: Language=None,
                                 target_language: Language=None,
                                 vendor_name=None,
                                 vendor_name_partial=None):
        params = {}
        if source_language:
            params['source_language_id'] = source_language.value
        if target_language:
            params['target_language_id'] = target_language.value
        if vendor_name:
            params['vendor_name'] = vendor_name
        if vendor_name_partial:
            params['vendor_name_cont'] = vendor_name_partial

        r = cls.get('translation_service_options', params=params)
        return r

    @classmethod
    def order_transcription(cls, video_id: str, video_name: str,
                            language: Language,
                            turnaround_level: Turnaround = Turnaround.STANDARD,
                            callback=None,
                            file_name: str = None, integration_id=None,
                            attr1: str = None, attr2: str = None, attr3: str = None,
                            labels: Optional[Dict[str, Any]] = None) -> (int, bool):
        """
        Orders a transcription for a video. The `video_id` is unique to the
        platform (ex. YouTube or Wistia) tied to the integration for the
        project.

        Returns a two-element tuple of (media_file_id, success) where the
        `success` indicates whether an order was successfully placed.

        """
        file_id = cls.create_media_file(
            video_id, video_name, language, file_name, integration_id,
            attr1, attr2, attr3, labels)

        success = cls.order_transcription_for_media_file(
            file_id, turnaround_level, callback)

        return file_id, success

    @classmethod
    def create_media_file(cls, video_id: str, video_name: str, language: Language,
                          file_name: str = None, integration_id=None,
                          attr1: str = None, attr2: str = None, attr3: str = None,
                          labels: Optional[Dict[str, Any]] = None):
        """
        Creates a media file on 3Play, which serves as a reference for the
        integration service.

        Any transcripts can be ordered on media files.
        """
        if not file_name:
            file_name = video_name

        labels = [f'{label}:{value}' for label, value in labels.items()]

        params = {'language_id': language.value,
                  'name': file_name,
                  'attribute1': attr1,
                  'attribute2': attr2,
                  'attribute3': attr3,
                  'label': ','.join(labels),
                  'reference_id': video_id,
                  'integration_id': integration_id or INTEGRATION_ID}

        r = cls.request('POST', 'files', params=params)
        file_id = r['data']['id']

        return file_id

    @classmethod
    def order_transcription_for_media_file(
            cls, media_file_id: int,
            turnaround_level: Turnaround = Turnaround.STANDARD,
            callback=None, read_timeout=2) -> bool:
        """
        Attempt to place a transcript order on a media file, and return
        a `success` indicating whether the order was placed successfully.

        Read the docs on fn:`_order_transcription_service` for more information.

        """
        params = {'media_file_id': media_file_id,
                  'turnaround_level_id': turnaround_level.id}
        if callback:
            params['callback'] = callback

        return cls._order_transcription_service(
            'transcription', params, read_timeout)

    @classmethod
    def import_transcript(cls, media_file_id: int,
                          caption_file_contents: str, language: Language,
                          auto_paragraph=True):
        """
        Import a transcript to a media file.
        """
        params = {'media_file_id': media_file_id,
                  'language_id': language.value,
                  'autoparagraph': str(auto_paragraph).lower()}

        files = {'caption_file': ('captions.srt', caption_file_contents)}

        r = cls.request('POST', 'transcripts/order/import',
                        params=params, files=files)

        return r

    @classmethod
    def order_audio_description_for_media_file(
            cls, media_file_id: int,
            turnaround_level: TurnaroundAD = TurnaroundAD.STANDARD,
            extended: bool = False,
            callback=None, read_timeout=2) -> bool:
        """
        Attempt to place an audio description order on a media file, and return
        a `success` indicating whether the order was placed successfully.

        If `extended` is true, order the Extended ADs instead. Note that some
        platforms (such as Wistia) currently only support Standard ADs.

        """
        timeout = Timeout(read=read_timeout or None)

        params = {'media_file_id': media_file_id,
                  'extended': str(extended).lower(),
                  'turnaround_level_id': turnaround_level.id}
        if callback:
            params['callback'] = callback

        try:
            _ = cls.request('POST', 'audio_descriptions/order',
                            params=params, timeout=timeout)

        except RequestException as e:
            if e.response is not None and e.response.status_code == 403:
                # HTTP Forbidden (403) means an Audio description is already in progress
                LOG.warning('Audio description already exists for media file: %d',
                            media_file_id)
                return True

            # Any other issues, such as 5xx status codes or a timeout raised
            # after `read_timeout` seconds, means the 3Play API could be
            # currently having issues, so we will need to retry the request
            # at a later time.
            return False

        return True

    @classmethod
    def order_translation(cls, media_file_id: int,
                          source_language: Language, target_language: Language,
                          source_transcript_id: int = None):

        translation_option = TranslationOption.get(source_language, target_language)

        params = {'media_file_id': media_file_id,
                  'translation_service_option_id': translation_option.value}
        if source_transcript_id:
            params['source_transcript_id'] = source_transcript_id

        return cls.request('POST', 'transcripts/order/translation', params=params)

    @classmethod
    def order_asr(cls, video_id: str, video_name: str, language: Language,
                  file_name: str = None, integration_id=None, callback=None,
                  attr1: str = None, attr2: str = None, attr3: str = None,
                  labels: Optional[Dict[str, Any]] = None):
        """
        Order Automated Speech Recognition (ASR) for a video.
        """
        file_id = cls.create_media_file(
            video_id, video_name, language, file_name, integration_id,
            attr1, attr2, attr3, labels)

        success = cls.order_asr_for_media_file(
            file_id, callback)

        return file_id, success

    @classmethod
    def order_asr_for_media_file(
            cls, media_file_id: int,
            callback=None, read_timeout=2) -> bool:
        """
        Attempt to place an ASR order on a media file, and return
        a `success` indicating whether the order was placed successfully.
        """
        params = {'media_file_id': media_file_id}
        if callback:
            params['callback'] = callback

        return cls._order_transcription_service(
            'asr', params, read_timeout)

    @classmethod
    def _order_transcription_service(cls, service: str,
                                     params: Dict, read_timeout: Optional[int]) -> bool:
        """
        Attempt to order a transcription service for a media file, and return
        a `success` indicating whether the order was placed successfully.

        The 3Play 'Order Transcripts' API is generally pretty slow (on
        average a call takes about ~10 seconds), which can sometimes spike
        up to a minute when their API is under heavy load, so we only wait
        up to `read_timeout` seconds for a response from 3Play. If there is
        no response within that time or a 5xx status response is returned
        instead, we should implement any necessary logic to retry the request
        at a later time.

        """
        timeout = Timeout(read=read_timeout or None)

        try:
            _ = cls.request('POST', f'transcripts/order/{service}',
                            params=params, timeout=timeout)

        except RequestException as e:
            if e.response is not None and e.response.status_code == 400:
                # HTTP Bad Request (400) means transcript is already in progress
                service_name = 'Transcript' if 'TRANSCRIPT' in service.upper() \
                    else f'Transcript ({service.capitalize()})'
                LOG.warning('%s already exists for media file: %d',
                            service_name, params.get('media_file_id'))
                return True

            # Any other issues, such as 5xx status codes or a timeout raised
            # after `read_timeout` seconds, means the 3Play API could be
            # currently having issues, so we will need to retry the request
            # at a later time.
            return False

        return True

    @classmethod
    def get_formatted_transcript_text(
            cls, transcript_id: int,
            start_seconds: Union[str, int, float, None] = None,
            output_format=TranscriptFormat.SRT,
            clips: Optional[List[str]] = None,
            log_level=INFO) -> str:
        """
        Get formatted text (SRT contents by default) for a given transcript.

        `start_seconds` is the number of seconds to cut from the start of the
        captions. You can also specify milliseconds if you pass it as a string,
        for example "32.012".

        `clips` is the portion of the captions to keep, for example if a cut
        was made in the middle of a video. It can be passed as an array
        of millisecond pairs, like ['0,10500', '21060,28140']

        """
        params = {'output_format_id': output_format.value}
        if start_seconds:
            params['offset'] = f'-{start_seconds}s'
        if clips:
            params['clips[]'] = clips

        res = cls.get(f'transcripts/{transcript_id}/text',
                      params=params, log_level=log_level)

        # The 'data' field contains the formatted text
        return res.get('data', '')

    @classmethod
    def get_transcript(cls, transcript_id=None):

        data = cls.request('GET', f'transcripts/{transcript_id}')

        return data

    @classmethod
    def get_transcripts(cls, transcript_id=None, media_file_id=None, media_file_name=None,
                        attr1: str = None, attr2: str = None, attr3: str = None,
                        label: str = None, by_default=False,
                        status: TranscriptStatus = None, language: Language = None, video_id=None,
                        per_page=100, sort_by_created=False, latest_first=False):
        params = {'per_page': per_page}
        if transcript_id:
            params['id'] = int(transcript_id)
        if media_file_id:
            params['media_file_id'] = int(media_file_id)
        if media_file_name:
            params['media_file_name'] = media_file_name
        if attr1:
            params['media_file_attribute1'] = attr1
        if attr2:
            params['media_file_attribute2'] = attr2
        if attr3:
            params['media_file_attribute3'] = attr3
        if label:
            params['media_file_label'] = label
        if status:
            params['status'] = status.value
        if language:
            params['language_id'] = language.value
        if video_id:
            params['media_file_reference_id'] = video_id
        if sort_by_created:
            params['sort_by'] = 'created_at'
            if latest_first:
                params['sort_dir'] = 'desc'
        if by_default:
            params['default'] = 'true'

        data = cls.request('GET', 'transcripts', params=params)
        # This might be a bug, but I noticed that sometimes when requesting
        # 'complete' transcripts, we also get a few 'in progress' transcripts
        if status:
            results = data.get('data', [])
            data['data'] = [r for r in results if r['status'] == status.value]

        return data

    @classmethod
    def list_audio_descriptions(
            cls, transcript_id=None, media_file_id=None, media_file_name=None,
            attr1: str = None, attr2: str = None, attr3: str = None,
            status: TranscriptStatus = None,
            language: Language = None, video_id=None, per_page=100,
            sort_by_created=False,
            created_after: datetime = None):
        params = {'per_page': per_page}
        if transcript_id:
            params['id'] = int(transcript_id)
        if media_file_id:
            params['media_file_id'] = int(media_file_id)
        if media_file_name:
            params['media_file_name'] = media_file_name
        if attr1:
            params['media_file_attribute1'] = attr1
        if attr2:
            params['media_file_attribute2'] = attr2
        if attr3:
            params['media_file_attribute3'] = attr3
        if status:
            params['status'] = status.value
        if language:
            params['language_id'] = language.value
        if video_id:
            params['media_file_reference_id'] = video_id
        if sort_by_created:
            params['sort_by'] = 'created_at'
        if created_after:
            if created_after.tzinfo is None:
                raise Exception('The input must not be a naive datetime')
            params['media_file_created_after'] = created_after.isoformat()

        return cls.request('GET', 'audio_descriptions', params=params).get('data') or []

    @classmethod
    def get_translation(cls, media_file_id=None, transcript_id=None):
        transcript_data = cls.get_transcripts(transcript_id, media_file_id)
        for transcript in transcript_data['data']:
            if transcript['type'] == 'TranslatedTranscript':
                return transcript
        return None

    @classmethod
    def get_media_file(cls, media_file_id: int):
        return cls.get(f'files/{media_file_id}')

    @classmethod
    def archive_media_file(cls, media_file_id: Union[int, List[int]]) -> bool:
        """
        Archive one or more media files.
        """
        if isinstance(media_file_id, list):
            media_file_id = ','.join(str(file_id) for file_id in media_file_id)
        params = {'media_file_id': media_file_id}

        res = cls.request('POST', f'files/archive', params=params)
        return res.get('data', {}).get('success') is True

    @classmethod
    def list_media_files(cls, name=None, name_partial=None,
                         video_id=None,
                         attr1: str = None, attr2: str = None, attr3: str = None,
                         per_page=100, sort_by_created=False,
                         latest_first=False):

        params = {'per_page': per_page}
        if name:
            params['name'] = name
        if name_partial:
            params['name_cont'] = name_partial
        if attr1:
            params['attribute1'] = attr1
        if attr2:
            params['attribute2'] = attr2
        if attr3:
            params['attribute3'] = attr3
        if video_id:
            params['reference_id'] = video_id
        if sort_by_created:
            params['sort_by'] = 'created_at'
            if latest_first:
                params['sort_dir'] = 'desc'

        return cls.get('files', params=params)

    @classmethod
    def cancel_transcript(cls, transcript_id: int):
        """
        Attempt to cancel a 3Play transcript, and return a value
        indicating whether the cancellation was a success.
        """
        try:
            cls.request('POST', f'transcripts/{transcript_id}/cancel')
            return True
        except HTTPError:
            return False

    @classmethod
    def redeliver_transcript(cls, transcript_id: int, service='wistia') -> bool:
        """
        Redelivers a transcript, e.g. triggers the postback, to an integration
        (defaults to Wistia) with the captions

        Returns a Boolean indicating whether the delivery was a success or not.
        """
        response = cls.request('POST', f'transcripts/{transcript_id}/redeliver')

        for delivery in response['data']:
            if delivery['method'] == service and delivery['success']:
                return True

        return False

    @classmethod
    def callback(cls, transcript_id: int):
        response = cls.request('POST', f'transcripts/{transcript_id}/callback')

        return response

    @classmethod
    def get_source(cls, media_file_id: int) -> Optional[str]:
        """Get the media source for a file."""
        file_data = cls.get_media_file(media_file_id)['data']
        return file_data.get('source')

    @classmethod
    def set_source_url(cls, media_file_id: int, source_url: str):
        params = {'source_url': source_url}
        response = cls.request('POST', f'files/{media_file_id}/source/set_url', params=params)

        return response

    @classmethod
    def delete_source(cls, media_file_id: int):
        response = cls.request('DELETE', f'files/{media_file_id}/source')

        return response

    @classmethod
    def get_ad_asset_url(cls, video_id: Optional[str] = None, ad_id: Optional[int] = None,
                         media_format='mp3') -> Optional[str]:
        """
        Get a downloadable link for audio description media (description and source mixed)

        Raises an :class:`ThreePlayError` if the latest audio description order
        is currently in progress.

        """
        if video_id:
            ad_orders = cls.list_audio_descriptions(
                video_id=video_id, sort_by_created=True)

            # Iterate over list with most recent order first
            for ad_order in reversed(ad_orders):
                ad_status = TranscriptStatus(ad_order['status'])
                if ad_status is TranscriptStatus.COMPLETE:
                    ad_id = ad_order['id']
                    break
                elif ad_status in (TranscriptStatus.PENDING, TranscriptStatus.IN_PROGRESS):
                    raise ADIsNotComplete(video_id)

            if not ad_id:
                return None

        params = {'format': media_format}

        r = cls.request('GET', f'audio_descriptions/{ad_id}/mix', params=params)
        url = r['data']

        return url

    @classmethod
    def download_ad_asset(
            cls, video_id: Optional[str] = None, ad_id: Optional[int] = None,
            media_format='mp3') -> bytes:
        """
        Download audio description media (description and source mixed)

        Returns the downloaded mp3 file as bytes

        """
        url = cls.get_ad_asset_url(video_id, ad_id, media_format)

        r = Session().get(url)
        r.raise_for_status()

        return r.content

    @classmethod
    def get_expiring_edit_url(
            cls, video_id: Optional[str] = None, transcript_id: Optional[int] = None,
            expiration_hours: int = 24) -> Optional[str]:
        """
        Get an expiring editing link for a `transcript_id` (or the latest transcript
        for a `video_id`).

        By default, the link will be valid for up to a day.
        """
        params = {'hours_until_expiration': expiration_hours}

        if video_id:
            LOG.info('%s: Retrieving latest transcript for video', video_id)

            transcript_orders = cls.get_transcripts(
                video_id=video_id, sort_by_created=True)['data']

            if not transcript_orders:
                return None

            transcript_id = transcript_orders[-1]['id']

        r = cls.request(
            'GET', f'transcripts/{transcript_id}/expiring_editing_link',
            params=params)

        url = r['data']
        return url
