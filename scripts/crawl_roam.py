"""
Downloads and parses some public databases from `https://github.com/br-g/roam-public-db`.
Parsing is done using my new Python package: pyroaman (https://github.com/br-g/pyroaman).

If you think some other databases should be added, please suggest it on Slack or
create a Github issue.
"""

from typing import Iterator, Dict
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from six.moves import urllib
import pytz
from loguru import logger
import click
from tqdm import tqdm
import pyroaman
from roam_sanity.util import save_as_json


DATABASES = [
    'help',
    'roamhacker',
]

parsing_time = datetime.now().astimezone(pytz.utc).isoformat()


def download_database(db_id: str) -> pyroaman.database:
    url = f'https://raw.githubusercontent.com/br-g/roam-public-db/main/json/{db_id}.json'
    dirpath = Path(tempfile.mkdtemp())
    filepath = dirpath / 'db.json'

    urllib.request.urlretrieve(url, filepath)
    db = pyroaman.load(filepath)
    shutil.rmtree(dirpath)

    return db


def timestamp_to_iso(timestamp: int) -> str:
    timestamp /= 1000  # type: ignore
    return datetime.fromtimestamp(timestamp).astimezone(pytz.utc).isoformat()


def render_block_content(block: 'pyroaman.Block') -> str:
    """Generates some HTML"""
    html = block.string
    html += '<ul>'
    for child in block.children:
        html += '<li>' + render_block_content(child) + '</li>'
    html += '</ul>'
    return html


def render_page_content(page: 'pyroaman.Block') -> str:
    """Generates some HTML"""
    html = '<ul>'
    for child in page.children:
        html += '<li>' + render_block_content(child) + '</li>'
    html += '</ul>'
    return html


def parse_database(db_id: str, db: pyroaman.database) -> Iterator[Dict]:
    for page in tqdm(db.pages):
        if 'uid' not in page.metadata:
            continue
        if not page.text:
            continue

        res = {
            'source': 'roam-research',
            'database': db_id,
            'parsing_time': parsing_time,
            'title': page.string,
            'url': f"https://roamresearch.com/#/app/{db_id}/page/{page.metadata['uid']}",
            'text': render_page_content(page)
        }
        if 'create-time' in page.metadata:
            res['create_time'] = timestamp_to_iso(page.metadata['create-time'])
        if 'edit-time' in page.metadata:
            res['edit_time'] = timestamp_to_iso(page.metadata['edit-time'])

        yield res


@click.command()
def main():
    for db_id in DATABASES:
        logger.info(f'Downloading `{db_id}`')
        db = download_database(db_id)

        logger.info(f'Parsing `{db_id}`')
        parsed = list(parse_database(db_id, db))
        logger.info(f'Collected {len(parsed)} blocks')

        logger.info(f'Saving `{db_id}`')
        for p in parsed:
            save_as_json(p)


if __name__ == '__main__':
    main()
