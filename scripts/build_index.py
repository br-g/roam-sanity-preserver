import os
from pathlib import Path
from loguru import logger
import click
from roam_sanity.indexing import index


@click.command()
@click.option('--data_path', type=str, default=os.environ['RSP_DATA_PATH'] if 'RSP_DATA_PATH' in os.environ else None, nargs=1, show_default=False)
def main(data_path: str):
    logger.info('Building Elasticsearch index')
    index.populate(Path(data_path))


if __name__ == '__main__':
    main()
