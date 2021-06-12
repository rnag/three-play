import pytest

from three_play.v3 import ThreePlayApi

# TODO Update as needed
API_KEY = 'TODO-REPLACE-ME'


@pytest.fixture(autouse=True, scope='session')
def setup_env():
    ThreePlayApi.configure(API_KEY)
