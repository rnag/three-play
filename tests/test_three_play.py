#!/usr/bin/env python

"""Tests for `three-play` package."""
import pytest

from three_play.errors import InvalidTurnaround
from three_play.v3 import *
from three_play.v3.models import *


def test_list_media_files(setup_env):
    list_of_dict = ThreePlayApi.list_media_files()['data']

    print(f'Found {len(list_of_dict)} media files in the 3Play account')
    # Note: some accounts can have a *lot* of files
    # print(list_of_dict)
    print()

    files = [MediaFile(**file) for file in list_of_dict]
    sample_files = files[:5]
    print(f'Printing first {len(sample_files)} MediaFile objects:')
    for mf in sample_files:
        print(f'  {mf}')


def test_helper_as_turnaround(setup_env):
    with pytest.raises(InvalidTurnaround):
        _ = ThreePlayHelper.as_turnaround('Testing')

    t = ThreePlayHelper.as_turnaround('Two hour')
    assert t is Turnaround.TWO_HOUR

    t = ThreePlayHelper.as_turnaround('STANDARD', cls=TurnaroundAD)
    assert type(t) is not Turnaround
    assert t is TurnaroundAD.STANDARD
