from typing import Dict, List, Tuple
import json
import time
from pathlib import Path
from tqdm import tqdm
from loguru import logger
from cached_property import cached_property
import elasticsearch
from roam_sanity.util import get_by_extension


# Settings for Elasticsearch
ANALYZER_SETTINGS = {
    'settings': {
        'analysis': {
            'filter': {
                'filter_stemmer': {
                    'type': 'stemmer',
                    'language': 'english'
                }
            },
            'analyzer': {
                'tags_analyzer': {
                    'type': 'custom',
                    'filter': [
                        'lowercase',
                        'filter_stemmer',
                        'asciifolding',
                    ],
                    'tokenizer': 'standard'
                }
            }
        }
    },
    'mappings': {
        'properties': {
            'text': {
                'type': 'text',
                'analyzer': 'tags_analyzer',
                'search_analyzer': 'tags_analyzer',
                'index': True
            },
            'url': {
                'type': 'text',
                'analyzer': 'whitespace',
                'search_analyzer': 'whitespace',
                'index': True
            },
            'source': {
                'type': 'text',
                'analyzer': 'whitespace',
                'search_analyzer': 'whitespace',
                'index': True
            },
        }
    }
}


class _Index:
    def __init__(self, name: str):
        self.name = name
        if not self.es_client.indices.exists(index=self.name):
            self.es_client.indices.create(self.name, body=ANALYZER_SETTINGS)

    @cached_property
    def es_client(self):  # pylint: disable=no-self-use
        es = elasticsearch.Elasticsearch()

        logger.info('Waiting for Elasticsearch')
        while True:
            try:
                es.search(index='')
                break
            except (elasticsearch.exceptions.ConnectionError,
                    elasticsearch.exceptions.TransportError):
                time.sleep(1)

        return es

    def populate(self, data_path: Path):
        """Loads JSON files from disk and populates Elasticsearch"""
        self.empty()

        paths = list(get_by_extension(data_path, 'json'))
        for path in tqdm(paths):
            with open(path, 'r') as f:
                obj = json.load(f)
                try:
                    self.add(obj)
                except:
                    print(obj)

    def add(self, doc: Dict):
        self.es_client.index(index=self.name, body=doc)

    def get(self, **kwargs) -> List[Dict]:
        res = self.es_client.search(
            index=self.name,
            body={
                'query': {
                    'bool': {
                        'must': [
                            {'term': {k: v}}
                            for k, v in kwargs.items()
                        ]
                    }
                }
            }
        )
        return [e['_source'] for e in res['hits']['hits']]

    def contains(self, doc: Dict) -> bool:
        return bool(self.get(url=doc['url']))

    def search(self, query: str, k: int) -> List[Tuple[float, Dict]]:
        res = self.es_client.search(
            index=self.name,
            body={
                'query': {
                    'match' : {
                        'text': {
                            'query': query,
                            'fuzziness': 0
                        }
                    }
                },
                'size': k
            }
        )

        return [(e['_score'], e['_source']) for e in res['hits']['hits']]

    def empty(self):
        self.es_client.indices.delete(index=self.name, ignore=[400, 404])  # pylint: disable=unexpected-keyword-arg
        self.__init__(self.name)


index = _Index('rsp')
