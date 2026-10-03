"""Подключение к собственной базе сервиса."""

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine


class Database:
    """Ленивая обёртка над движком SQLAlchemy.

    Движок и пул создаются при первом обращении, поэтому импорт модуля сервиса
    (например, в unit-тестах с подменённым репозиторием) не требует живого Postgres.
    """

    def __init__(self, database_url: str, *, echo: bool = False) -> None:
        self._database_url = database_url
        self._echo = echo
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        if self._session_factory is None:
            self._engine = create_async_engine(self._database_url, echo=self._echo, pool_pre_ping=True)
            self._session_factory = async_sessionmaker(
                bind=self._engine, expire_on_commit=False, autoflush=False
            )
        return self._session_factory

    async def dispose(self) -> None:
        if self._engine is not None:
            await self._engine.dispose()
