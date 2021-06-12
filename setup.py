#!/usr/bin/env python

"""The setup script."""

from setuptools import setup, find_packages

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = ['requests']

test_requirements = ['pytest>=3', ]

setup(
    author='Ritvik Nag',
    author_email='rv.kvetch@gmail.com',
    python_requires='>=3.7',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
    ],
    description='A Python wrapper library for the 3Play API v3',
    install_requires=requirements,
    license='MIT license',
    long_description=readme + '\n\n' + history,
    include_package_data=True,
    keywords=['three play', 'threeplay', '3play', '3play api v3'],
    name='three-play',
    packages=find_packages(include=['three_play', 'three_play.*']),
    test_suite='tests',
    tests_require=test_requirements,
    url='https://github.com/rnag/three-play',
    version='0.1.1',
    zip_safe=False,
)
