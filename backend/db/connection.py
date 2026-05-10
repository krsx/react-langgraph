import mysql.connector
from mysql.connector.pooling import MySQLConnectionPool
from config import get_config

_pool: MySQLConnectionPool | None = None


def _get_pool() -> MySQLConnectionPool:
    global _pool
    if _pool is None:
        cfg = get_config()
        _pool = MySQLConnectionPool(
            pool_name="csagent_pool",
            pool_size=int(__import__("os").environ.get("MYSQL_POOL_SIZE", "5")),
            host=cfg.MYSQL_HOST,
            port=cfg.MYSQL_PORT,
            user=cfg.MYSQL_USER,
            password=cfg.MYSQL_PASSWORD,
            database=cfg.MYSQL_DATABASE,
        )
    return _pool


def get_connection() -> mysql.connector.MySQLConnection:
    return _get_pool().get_connection()
