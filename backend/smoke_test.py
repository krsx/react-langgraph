"""
Run after `docker compose up mysql` to verify MySQL and LLM connectivity.
Usage: python smoke_test.py
"""
import sys
from dotenv import load_dotenv

load_dotenv()

from config import get_config
from db.connection import get_connection
from llm_factory import create_llm


def check_mysql():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM orders")
    count = cursor.fetchone()[0]
    conn.close()
    print(f"[mysql] OK — {count} orders in seed data")


def check_llm():
    llm = create_llm()
    response = llm.invoke("Reply with the single word: pong")
    print(f"[llm]   OK — response: {response.content.strip()}")


if __name__ == "__main__":
    cfg = get_config()
    print(f"Provider URL : {cfg.LLM_PROVIDER_URL}")
    print(f"Model        : {cfg.DEFAULT_MODEL}")
    print(f"MySQL        : {cfg.MYSQL_HOST}:{cfg.MYSQL_PORT}/{cfg.MYSQL_DATABASE}")
    print()

    errors = []

    try:
        check_mysql()
    except Exception as e:
        errors.append(f"[mysql] FAIL — {e}")

    try:
        check_llm()
    except Exception as e:
        errors.append(f"[llm]   FAIL — {e}")

    if errors:
        for err in errors:
            print(err, file=sys.stderr)
        sys.exit(1)
