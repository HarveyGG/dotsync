from dataclasses import dataclass
from typing import List


@dataclass
class TreeEntry:
    pattern: str
    categories: List[str]
    plugin: str = 'plain'
