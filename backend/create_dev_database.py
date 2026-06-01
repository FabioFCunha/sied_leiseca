import psycopg2
from decouple import config


def main():
    database = "agenda_eventos"
    connection = psycopg2.connect(
        dbname="postgres",
        user=config("POSTGRES_USER"),
        password=config("POSTGRES_PASSWORD"),
        host=config("POSTGRES_HOST", default="localhost"),
        port=config("POSTGRES_PORT", default="5432"),
    )
    connection.autocommit = True
    cursor = connection.cursor()
    cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (database,))
    if not cursor.fetchone():
        cursor.execute(f'CREATE DATABASE "{database}"')
    print(f"Banco {database} pronto.")


if __name__ == "__main__":
    main()
