__all__ = ['total_seconds',
           'total_ms',
           'timestamp',
           'get_srt_duration',
           'remove_dialogue_for_first_ts',
           'remove_dialogue_between']

from datetime import timedelta
from functools import reduce


def total_seconds(ts: str) -> str:
    """
    Converts a timestamp containing hours, minutes, seconds, and milliseconds
    (for example, in the "HH:mm:ss,SSS" format) to a string representing the
    total seconds, along with the millisecond part.

    For example, a string like "1:20:32,5" will be returned as "4832.005"

    Supports parsing the following input formats:
        - (H)H:mm:ss,SSS
        - (H)H:mm:ss.SSS
        - (H)H:mm:ss:SSS

    A modified version of the following (great) solution:
    https://stackoverflow.com/a/57610198

    """
    seconds, milliseconds = divmod(total_ms(ts), 1000)

    return f'{seconds}.{milliseconds:0>3}'


def total_ms(ts: str) -> int:
    """
    Converts a timestamp containing hours, minutes, seconds, and milliseconds
    (for example, in the "HH:mm:ss,SSS" format) to an integer value representing
    the total milliseconds.

    For example, a string like "1:20:32,5" will be returned as 4832005

    Supports parsing the following input formats:
        - (H)H:mm:ss,SSS
        - (H)H:mm:ss.SSS
        - (H)H:mm:ss:SSS

    A modified version of the following (great) solution:
    https://stackoverflow.com/a/57610198

    """
    try:
        h_m_s, milliseconds = ts.replace('.', ',').rsplit(',', 1)
    except ValueError:
        h_m_s, milliseconds = ts.rsplit(':', 1)

    seconds = reduce(lambda sum, d: sum * 60 + int(d), h_m_s.split(':'), 0)

    return (seconds * 1000) + int(milliseconds)


def timestamp(seconds: float = 0, *,
              hours: float = 0, minutes: float = 0, milliseconds: float = 0):
    """
    Convert a duration (generally specified in seconds) to a formatted string
    in the 'HH:mm:ss.SSS' format, for example '2:01:03.150'.
    """
    kwargs = locals()
    ts = str(timedelta(**kwargs))
    if '.' in ts:
        # Replace the microsecond part with milliseconds
        return ts[:-3]
    return ts


def get_srt_duration(srt_contents: str, default_end_seconds=0.0) -> float:
    """
    Gets the total duration (based on end timestamp) of an SRT file
    """
    caption_text = srt_contents.split('\n')
    captions_end_seconds = default_end_seconds
    following_line = ''

    for line in reversed(caption_text):
        if '-->' in line:
            # Fix: sometimes the durations will be listed for
            # a blank line (no dialogue)
            if not following_line.strip():
                continue

            end = line.replace(' ', '').rsplit('-->', 1)[-1]
            captions_end_seconds = float(total_seconds(end))
            break

        following_line = line

    return captions_end_seconds


def remove_dialogue_for_first_ts(srt_contents: str, ts: str) -> str:
    """
    Removes dialogue under the first occurrence of a start timestamp
    in an SRT file. If the start timestamp is not found, return
    the `srt_contents` instead.

    """
    caption_text = srt_contents.split('\n')

    for i, line in enumerate(caption_text):
        if '-->' in line:
            start_ts = line.split('-->', 1)[0].strip()

            if start_ts == ts:
                split_ind = i + 1
                for j in range(split_ind, len(caption_text)):
                    if not caption_text[j].strip():
                        # Found the next blank line
                        split_ind = j
                        break

                # Return SRT contents with the first dialogue for that timestamp removed
                return '\n'.join(caption_text[:i+1] + caption_text[split_ind:])

    return srt_contents


def remove_dialogue_between(srt_contents: str, start_ms: int, end_ms: int):
    """
    Remove all dialogue between `start_ms` and `end_ms`, non-inclusive of any
    dialogue for `end_ms` - note that values are in milliseconds.

    """
    caption_text = srt_contents.split('\n')
    srt_lines = []  # Lines to keep
    exclude_dialogue = False

    for line in caption_text:
        if '-->' in line:
            start_ts = line.split('-->', 1)[0].strip()
            line_ts_ms = total_ms(start_ts)
            if start_ms <= line_ts_ms < end_ms:
                # If start timestamp of the line is between start_ts and end_ms,
                # exclude all of its dialogue
                exclude_dialogue = True

        elif exclude_dialogue:
            if line.strip():
                continue
            else:
                # Found blank line
                exclude_dialogue = False

        srt_lines.append(line)

    return '\n'.join(srt_lines or caption_text)
