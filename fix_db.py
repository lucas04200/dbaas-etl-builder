import psycopg2
import os

# DataForge — DB Table Creator
DB_HOST = os.getenv("DATAFORGE_DB_HOST", "localhost")
DB_NAME = os.getenv("DATAFORGE_DB_NAME", "dataforge")
DB_USER = os.getenv("DATAFORGE_DB_USER", "dataforge")
DB_PASS = os.getenv("DATAFORGE_DB_PASS", "DataForge_Internal_2024!")
DB_PORT = os.getenv("DATAFORGE_DB_PORT", "5433")

SQL = """
CREATE TABLE IF NOT EXISTS metabase_connections (
    metabase_id INTEGER NOT NULL REFERENCES metabase_instances(id) ON DELETE CASCADE,
    pg_id       INTEGER NOT NULL REFERENCES postgres_instances(id) ON DELETE CASCADE,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (metabase_id, pg_id)
);

CREATE TABLE IF NOT EXISTS n8n_connections (
    n8n_id     INTEGER NOT NULL REFERENCES n8n_instances(id) ON DELETE CASCADE,
    pg_id      INTEGER NOT NULL REFERENCES postgres_instances(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (n8n_id, pg_id)
);

CREATE TABLE IF NOT EXISTS mage_connections (
    mage_id    INTEGER NOT NULL REFERENCES mage_instances(id) ON DELETE CASCADE,
    pg_id      INTEGER NOT NULL REFERENCES postgres_instances(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (mage_id, pg_id)
);

CREATE TABLE IF NOT EXISTS superset_connections (
    superset_id INTEGER NOT NULL REFERENCES superset_instances(id) ON DELETE CASCADE,
    pg_id       INTEGER NOT NULL REFERENCES postgres_instances(id) ON DELETE CASCADE,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (superset_id, pg_id)
);

CREATE TABLE IF NOT EXISTS airflow_connections (
    airflow_id INTEGER NOT NULL REFERENCES airflow_instances(id) ON DELETE CASCADE,
    pg_id      INTEGER NOT NULL REFERENCES postgres_instances(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (airflow_id, pg_id)
);
"""

def main():
    try:
        print(f"Connecting to {DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}...")
        conn = psycopg2.connect(
            host=DB_HOST,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            port=DB_PORT,
            connect_timeout=5
        )
        cur = conn.cursor()
        print("Creating connection tables...")
        cur.execute(SQL)
        conn.commit()
        print("Tables created successfully.")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")
        print("Retrying on 5432...")
        try:
             conn = psycopg2.connect(
                host=DB_HOST,
                dbname=DB_NAME,
                user=DB_USER,
                password=DB_PASS,
                port="5432",
                connect_timeout=5
            )
             cur = conn.cursor()
             cur.execute(SQL)
             conn.commit()
             print("Tables created successfully on 5432.")
             cur.close()
             conn.close()
        except Exception as e2:
             print(f"Error on 5432: {e2}")

if __name__ == "__main__":
    main()
