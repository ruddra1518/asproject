"""Azure Cosmos DB connector helpers.

Usage:
1. Install dependency: pip install azure-cosmos
2. Set environment variables: COSMOS_ENDPOINT, COSMOS_KEY
3. Import and call `get_container_from_env()` to get the container client.

This module targets the database `assignmentdb`, container `submissions`,
with partition key `/erp` as requested.
"""

import os
from typing import Optional

from azure.cosmos import CosmosClient, PartitionKey

DEFAULT_DATABASE = "assignmentdb"
DEFAULT_CONTAINER = "submissions"
DEFAULT_PARTITION = "/erp"


def get_cosmos_client(endpoint: Optional[str] = None, key: Optional[str] = None) -> CosmosClient:
    """Return a CosmosClient using given values or environment variables.

    Raises RuntimeError if credentials are missing.
    """
    endpoint = endpoint or os.getenv("COSMOS_ENDPOINT")
    key = key or os.getenv("COSMOS_KEY")

    if not endpoint or not key:
        raise RuntimeError("COSMOS_ENDPOINT and COSMOS_KEY environment variables must be set")

    return CosmosClient(endpoint, key)


def get_database(client: CosmosClient, database_name: str = DEFAULT_DATABASE):
    """Return a DatabaseProxy for `database_name` (creates if missing)."""
    return client.create_database_if_not_exists(id=database_name)


def get_container(
    client: CosmosClient,
    database_name: str = DEFAULT_DATABASE,
    container_name: str = DEFAULT_CONTAINER,
    partition_key: str = DEFAULT_PARTITION,
):
    """Return a ContainerProxy for the given names (creates if missing).

    Note: `create_container_if_not_exists` is safe to call in most deployment
    scenarios; if you prefer not to create containers from code, use
    `client.get_database_client(database_name).get_container_client(container_name)`
    instead and ensure the resources exist beforehand.
    """
    db = get_database(client, database_name)
    return db.create_container_if_not_exists(id=container_name, partition_key=PartitionKey(path=partition_key))


def get_container_from_env():
    """Convenience helper: build client and return the configured container.

    Reads `COSMOS_ENDPOINT` and `COSMOS_KEY` from environment.
    """
    client = get_cosmos_client()
    return get_container(client)


__all__ = [
    "get_cosmos_client",
    "get_database",
    "get_container",
    "get_container_from_env",
]
