"""Uso: python -m fatsecret "manzana" """

import json
import sys

from .client import FatSecretClient


def main():
    query = " ".join(sys.argv[1:]) or "apple"
    client = FatSecretClient()
    print(json.dumps(client.search_foods(query, max_results=5), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
