import psycopg
from fastapi import APIRouter
from neo4j import GraphDatabase
from neo4j.exceptions import DriverError, Neo4jError

from app.config import settings

router = APIRouter()


def _check_postgres() -> bool:
    try:
        with psycopg.connect(settings.postgres_dsn, connect_timeout=2) as conn:
            conn.execute("SELECT 1")
        return True
    except psycopg.Error:
        return False


def _check_neo4j() -> bool:
    try:
        driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
            connection_timeout=2.0,
        )
        driver.verify_connectivity()
        driver.close()
        return True
    except (DriverError, Neo4jError, OSError):
        return False


@router.get("/health")
def health():
    return {"api": "ok", "postgres": _check_postgres(), "neo4j": _check_neo4j()}