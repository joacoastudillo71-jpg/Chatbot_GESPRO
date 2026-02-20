import psycopg
from psycopg_pool import AsyncConnectionPool
from contextlib import asynccontextmanager
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from src.config.settings import settings

@asynccontextmanager
async def get_checkpointer():
    """
    Configura y entrega el checkpointer para LangGraph.
    """
    conn_kwargs = {
        "prepare_threshold": None,
        "autocommit": True
    }

    # Creamos el pool de conexiones
    async with AsyncConnectionPool(
        conninfo=settings.db_connection_string,
        kwargs=conn_kwargs,
        min_size=1,
        max_size=1
    ) as pool:
        # En versiones nuevas, simplemente instanciamos el objeto.
        # El pool se encarga de la conexión.
        checkpointer = AsyncPostgresSaver(pool)
        
        # Opcional: Esto asegura que las tablas existan
        await checkpointer.setup()
        
        yield checkpointer