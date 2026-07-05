import psycopg2
import psycopg2.extras

from app.config import settings


def _connect():
    return psycopg2.connect(
        host=settings.postgres_host,
        port=settings.postgres_port,
        dbname=settings.postgres_db,
        user=settings.postgres_user,
        password=settings.postgres_password,
    )


def get_project_by_subdomain(subdomain: str) -> dict | None:
    with _connect() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT id, name, subdomain FROM project WHERE subdomain = %s", (subdomain,))
        row = cur.fetchone()
        return dict(row) if row else None


def get_latest_ready_deployment(project_id: str) -> dict | None:
    with _connect() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            """
            SELECT id, project_id, status, created_at
            FROM deployment
            WHERE project_id = %s AND status = 'READY'
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (project_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None
