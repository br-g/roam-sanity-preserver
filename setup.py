"""Setup script"""

from distutils.core import setup
from setuptools import find_packages

with open('README.md', 'r') as fh:
    long_description = fh.read()

setup(
    name='roam_sanity',
    version='0.1.0',
    description='A search engine for everything related to Roam Research on the Web.',
    url = 'https://github.com/br-g/roam-sanity-preserver',
    ong_description=long_description,
    long_description_content_type='text/markdown',
    packages=find_packages(exclude=['tests']),
    python_requires='>=3.6',  # we can't upgrade because of deployment constraints
    install_requires=[
        'cached_property',
        'click',
        'elasticsearch>=7',
        'Flask',
        'loguru',
        'pathlib',
        'python-dateutil',
        'tqdm',
    ],
    extras_require={
        'crawl': [
            'bs4',
            'Markdown',
            'pyroaman',
            'python-twitter',
            'pytz',
            'selenium',
            'twint @ git+https://git@github.com/twintproject/twint.git@origin/master#egg=twint',
            'webdriver-manager',
        ]
    },
    classifiers=(
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3 :: Only'
    ),
)
