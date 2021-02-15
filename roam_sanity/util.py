from typing import Iterator, Dict
import re
import os
import json
from subprocess import Popen, PIPE
from pathlib import Path
import hashlib


def hash_(s: str) -> str:
    """Hash consistent across executions and platforms"""
    return hashlib.sha224(s.encode('utf-8')).hexdigest()


def save_as_json(doc: Dict):
    dir_path = Path(os.environ['RSP_DATA_PATH']) / doc['source']
    dir_path.mkdir(parents=True, exist_ok=True)
    key = hash_(doc['url'])

    with open(dir_path / f'{key}.json', 'w') as f:
        json.dump(doc, f, sort_keys=True, indent='\t')


def get_by_extension(path: Path, extension: str) -> Iterator[Path]:
    """Yields file paths matching an extension, from nested folders"""
    if path.is_dir():
        for p in path.iterdir():
            yield from get_by_extension(p, extension)
    else:
        if re.match(r"^.*\.{}$".format(extension), str(path)):
            yield path


def run_in_subprocess(cmd: str) -> str:
    pop = Popen(cmd, shell=True, stdin=PIPE, stderr=PIPE, stdout=PIPE,
                close_fds=True)
    pop.wait()
    if pop.returncode != 0:
        raise SystemError(pop.stderr.read().decode('utf-8'))  # type: ignore
    output = pop.stdout.read().decode('utf-8')  # type: ignore
    if output and output[-1] == '\n':
        output = output[:-1]
    return output
