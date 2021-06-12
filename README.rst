================
3Play API Helper
================


.. image:: https://img.shields.io/pypi/v/three-play.svg
        :target: https://pypi.python.org/pypi/three-play

.. image:: https://img.shields.io/travis/rnag/three-play.svg
        :target: https://travis-ci.com/rnag/three-play

.. image:: https://readthedocs.org/projects/three-play/badge/?version=latest
        :target: https://three-play.readthedocs.io/en/latest/?version=latest
        :alt: Documentation Status


.. image:: https://pyup.io/repos/github/rnag/three-play/shield.svg
     :target: https://pyup.io/repos/github/rnag/three-play/
     :alt: Updates



A Python wrapper library for the 3Play API v3


* Free software: MIT license
* Documentation: https://three-play.readthedocs.io.

Usage
-----

.. code-block:: python3

    from three_play.v3 import *
    from three_play.v3.models import *

    # Assuming you haven't set this via the environment variable
    ThreePlayApi.configure('MY-API-KEY')

    r = ThreePlayApi.list_media_files(name_partial='Testing')
    file_data = r.get('data', [])
    files = [MediaFile(**file) for file in file_data]
    print(len(files), files)

    transcripts = ThreePlayHelper.get_transcripts('my-video-id')
    print(len(transcripts), transcripts)

Installing
----------
The 3Play helper library is available on PyPI:

.. code-block:: shell

    $ python -m pip install three-play

Supported Versions
------------------
The ``three-play`` helper library officially supports **Python 3.7** or higher.

About
-----

I recommend reading the documentation in the source code
for important HOW-TO's and info on what each helper function is doing.

I'll need to write some kind of documentation eventually, but that's still pending for now.

At a minimum I recommend setting these 2 environment variables:

* ``3PLAY_API_KEY`` - API Key to use for requests to 3Play API

* ``INTEGRATION_ID`` - Service Integration ID on 3Play - for example, an integration /w YouTube

Features
--------

* TODO

Credits
-------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
