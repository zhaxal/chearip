from collections.abc import Iterator

import pytest
from sqlalchemy.orm import Session

from app.database import engine


@pytest.fixture
def db() -> Iterator[Session]:
    """A session on the local DB whose writes are rolled back after the test.

    `session.commit()` and `session.rollback()` inside a test only act on a
    savepoint, so the outer transaction can always be rolled back.
    """
    with engine.connect() as connection:
        transaction = connection.begin()
        session = Session(bind=connection, join_transaction_mode="create_savepoint")
        try:
            yield session
        finally:
            session.close()
            transaction.rollback()
