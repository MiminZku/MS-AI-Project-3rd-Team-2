from __future__ import annotations

import secrets
import string

from app.services.store import Store


_ACCESS_ID_ALPHABET = string.ascii_uppercase + string.digits


async def issue_project_access_id(store: Store) -> str:
    """Return a random, unique Client-facing project access identifier."""
    for _ in range(20):
        access_id = "PRJ-" + "".join(
            secrets.choice(_ACCESS_ID_ALPHABET)
            for _ in range(12)
        )
        if await store.get_study_by_access_id(access_id) is None:
            return access_id

    raise RuntimeError("Unable to generate a unique project access ID")
