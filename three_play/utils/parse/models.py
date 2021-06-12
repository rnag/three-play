from dataclasses import dataclass, field
from textwrap import wrap
from typing import List, Union, Type

from ...utils.parse import as_int
from ..types import R


# Default max line width for text wrapping
DEFAULT_LINE_WIDTH = 35


# Extend from List[T] so we can get type hinting when looping over,
# for example
class ListOfSRTLine(List['SRTLine']):

    def __init__(self, srt_contents: str):
        """
        Initialize a new :class:`ListOfSRTLine` object.

        :param srt_contents: SRT file contents, as a string
        """
        seq = (SRTLine.parse(lines)
               for lines in srt_contents.split('\n\n'))

        super().__init__(seq)

    @property
    def contents(self) -> str:
        """
        Return the SRT file contents, as a string
        """
        return '\n\n'.join(str(lines) for lines in self)

    def insert(self, __index: int, __object: 'SRTLine') -> None:
        """
        Insert a :class:`SRTLine` into the list at a specified index, and
        increment the line numbers for all subsequent lines as needed.

        """
        for rem_lines in self[__index:]:
            # Added because type hints don't automatically work here, for some reason
            rem_lines: SRTLine
            if not rem_lines.num:
                # Line number cannot be parsed to int
                rem_lines.num = __index + 1
            rem_lines.num += 1

        super(ListOfSRTLine, self).insert(__index, __object)


@dataclass(init=False)
class SRTLine:
    """
    Represents a sequence of dialogue lines in an SRT file.

    For each element in the sequence:
        * the first line will be the line number (ex. 12)

        * the second line will be the timeframe, which is formatted like so
          with an arrow denoting range:

            [First Timestamp] --> [Second Timestamp]

        * the remaining lines (can be empty) will be the dialogue

    """
    # The line number (as a string)
    num: int

    # The time range where the line should appear in the video
    time_range: str

    # The text (lines of dialogue) that should appear on the line
    dialogue: List[str]

    # The line width to wrap when `dialogue` is passed as a string
    width: int = field(repr=False)

    def __init__(self, num: Union[int, str] = 0, time_range: str = '',
                 dialogue: Union[List[str], str, None] = None,
                 width: int = DEFAULT_LINE_WIDTH):
        self.num = num
        self.time_range = time_range
        self.width = width
        self.dialogue = dialogue

    @classmethod
    def parse(cls: Type[R], lines: Union[str, List[str]]) -> R:
        """
        Parse and return a new :class:`SRTLine` object.

        :param lines: The lines from an SRT file, which should adhere
            to the sequence as specified in the class docs.

        """
        # Convert to a list if needed
        if isinstance(lines, str):
            lines = lines.strip().split('\n')
        # Unpack the list, save the remaining lines into `dialogue`
        line_num, time_range, *dialogue = lines
        # Returns the new object
        return cls(line_num, time_range, dialogue)

    @property
    def start_ts(self) -> str:
        """Return the start timestamp associated with the line."""
        return self.time_range.split('-->', 1)[0].strip()

    @property
    def end_ts(self) -> str:
        """Return the end timestamp associated with the line."""
        return self.time_range.rsplit('-->', 1)[-1].strip()

    @property
    def text(self) -> str:
        """Returns the dialogue as a string."""
        return ' '.join(line.strip() for line in self.dialogue)

    @property
    def num(self) -> int:
        return self._num

    @num.setter
    def num(self, n: Union[str, int], default=0):
        """Set the :attr:`num` attribute."""
        self._num = as_int(n, default, raise_=False)

    @property
    def dialogue(self) -> List[str]:
        return self._dialogue

    @dialogue.setter
    def dialogue(self, lines: Union[List[str], str, None]):
        """Set the dialogue for the line."""
        dialogue = lines or []
        if not isinstance(dialogue, list):
            dialogue = wrap(dialogue, width=self.width)
        self._dialogue = dialogue

    def set_time_range_if_empty(self, time_range: str):
        """Set the :attr:`time_range` attribute if it's empty or null."""
        if not self.time_range:
            self.time_range = time_range

    def __str__(self):
        """
        Returns the string representation of the line, as it would
        appear in an SRT file.
        """
        return '\n'.join([str(self.num), self.time_range, *self.dialogue])
