#!/usr/bin/env python3
"""
neon_sync.py — Trae datos desde una base Neon (Postgres) hacia tu Postgres
LOCAL, sin modificar nada en Neon (la conexión a Neon se abre en modo
solo-lectura, así que este script nunca puede escribir ahí).

Requisitos:
    pip install psycopg2-binary

Uso típico:

    # 0) Guardá las cadenas de conexión en variables de entorno (más seguro
    #    que pasarlas por línea de comando, quedan en el historial de la shell)
    export NEON_URL="postgresql://usuario:password@host/db?sslmode=require&channel_binding=require"
    export LOCAL_URL="postgresql://usuario:password@localhost:5432/tu_db_local"

    # 1) Ver qué tablas hay en Neon (por si no sabés el nombre exacto de la
    #    tabla de inscripciones a mesa final)
    python neon_sync.py list-tables --neon "$NEON_URL"

    # 2) Ver columnas y primary key de una tabla puntual
    python neon_sync.py describe --neon "$NEON_URL" --table nombre_tabla

    # 3) Sincronizar (upsert) esa tabla hacia tu Postgres local
    python neon_sync.py sync --neon "$NEON_URL" --local "$LOCAL_URL" --table nombre_tabla

    # Podés repetir --table para sincronizar varias tablas en una sola corrida:
    python neon_sync.py sync --neon "$NEON_URL" --local "$LOCAL_URL" \\
        --table inscripciones_mesafinal --table alumnos

Notas:
  - Requiere que la tabla ya exista en tu base local con el mismo nombre y
    las mismas columnas (correr las migraciones locales antes si hace falta).
  - Hace upsert por primary key: si la fila ya existe localmente la actualiza,
    si no existe la inserta. No borra filas locales que no estén en Neon.
  - Si una tabla no tiene primary key, el script avisa y no sincroniza esa
    tabla (no hay forma segura de hacer upsert sin una clave).
"""
import argparse
import sys

try:
    import psycopg2
    import psycopg2.extras
    from psycopg2 import sql
except ImportError:
    sys.exit("Falta psycopg2. Instalalo con: pip install psycopg2-binary")


def connect(url, read_only=False):
    conn = psycopg2.connect(url)
    if read_only:
        conn.set_session(readonly=True, autocommit=True)
    return conn


def get_columns(cur, table):
    cur.execute(
        """
        select column_name, data_type
        from information_schema.columns
        where table_schema = 'public' and table_name = %s
        order by ordinal_position
        """,
        (table,),
    )
    return cur.fetchall()


def get_primary_key(cur, table):
    cur.execute(
        """
        select kcu.column_name
        from information_schema.table_constraints tco
        join information_schema.key_column_usage kcu
          on kcu.constraint_name = tco.constraint_name
         and kcu.constraint_schema = tco.constraint_schema
        where tco.constraint_type = 'PRIMARY KEY'
          and tco.table_schema = 'public'
          and tco.table_name = %s
        order by kcu.ordinal_position
        """,
        (table,),
    )
    return [r[0] for r in cur.fetchall()]


def cmd_list_tables(args):
    conn = connect(args.neon, read_only=True)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                select table_name
                from information_schema.tables
                where table_schema = 'public'
                order by table_name
                """
            )
            tables = [r[0] for r in cur.fetchall()]
    finally:
        conn.close()

    if not tables:
        print("No encontré tablas en el schema 'public' de Neon.")
        return
    print("Tablas encontradas en Neon (schema public):")
    for t in tables:
        print(f"  - {t}")


def cmd_describe(args):
    conn = connect(args.neon, read_only=True)
    try:
        with conn.cursor() as cur:
            cols = get_columns(cur, args.table)
            pk = get_primary_key(cur, args.table)
    finally:
        conn.close()

    if not cols:
        sys.exit(f"No encontré la tabla '{args.table}' en Neon (schema public).")

    print(f"Tabla: {args.table}")
    print(f"Primary key: {pk or '(ninguna encontrada)'}")
    print("Columnas:")
    for name, dtype in cols:
        print(f"  - {name} ({dtype})")


def build_select(table, col_names):
    return sql.SQL("select {cols} from {table}").format(
        cols=sql.SQL(", ").join(map(sql.Identifier, col_names)),
        table=sql.Identifier(table),
    )


def build_upsert(table, col_names, pk):
    update_cols = [c for c in col_names if c not in pk]
    col_list = sql.SQL(", ").join(map(sql.Identifier, col_names))
    placeholders = sql.SQL(", ").join(sql.Placeholder() for _ in col_names)
    pk_list = sql.SQL(", ").join(map(sql.Identifier, pk))

    if update_cols:
        set_clause = sql.SQL(", ").join(
            sql.SQL("{c} = excluded.{c}").format(c=sql.Identifier(c))
            for c in update_cols
        )
        return sql.SQL(
            "insert into {table} ({cols}) values ({vals}) "
            "on conflict ({pk}) do update set {set_clause}"
        ).format(
            table=sql.Identifier(table),
            cols=col_list,
            vals=placeholders,
            pk=pk_list,
            set_clause=set_clause,
        )
    return sql.SQL(
        "insert into {table} ({cols}) values ({vals}) on conflict ({pk}) do nothing"
    ).format(table=sql.Identifier(table), cols=col_list, vals=placeholders, pk=pk_list)


def sync_one_table(neon_conn, local_conn, table, batch_size):
    with neon_conn.cursor() as cur:
        cols = get_columns(cur, table)
        pk = get_primary_key(cur, table)

    if not cols:
        print(f"[{table}] no existe en Neon (schema public) — salteando.")
        return
    if not pk:
        print(
            f"[{table}] no tiene primary key detectable, no puedo hacer "
            "upsert de forma segura — salteando."
        )
        return

    col_names = [c[0] for c in cols]

    with local_conn.cursor() as local_cur:
        local_cols = {c[0] for c in get_columns(local_cur, table)}
    missing = set(col_names) - local_cols
    if missing:
        print(
            f"[{table}] tu tabla local no tiene estas columnas: "
            f"{sorted(missing)}. Corré las migraciones locales para que el "
            "esquema coincida — salteando."
        )
        return

    select_sql = build_select(table, col_names)
    upsert_sql = build_upsert(table, col_names, pk)

    total = 0
    with neon_conn.cursor(name=f"neon_sync_{table}") as read_cur:
        read_cur.itersize = batch_size
        read_cur.execute(select_sql)
        with local_conn.cursor() as write_cur:
            while True:
                rows = read_cur.fetchmany(batch_size)
                if not rows:
                    break
                psycopg2.extras.execute_batch(write_cur, upsert_sql, rows)
                local_conn.commit()
                total += len(rows)
                print(f"[{table}] ... {total} filas sincronizadas", end="\r")
    print(f"\n[{table}] listo: {total} filas sincronizadas hacia tu base local.")


def cmd_sync(args):
    neon_conn = connect(args.neon, read_only=True)
    local_conn = psycopg2.connect(args.local)
    try:
        for table in args.table:
            sync_one_table(neon_conn, local_conn, table, args.batch_size)
    finally:
        neon_conn.close()
        local_conn.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list-tables", help="Listar tablas disponibles en Neon")
    p_list.add_argument("--neon", required=True, help="Connection string de Neon")
    p_list.set_defaults(func=cmd_list_tables)

    p_desc = sub.add_parser("describe", help="Ver columnas y primary key de una tabla en Neon")
    p_desc.add_argument("--neon", required=True, help="Connection string de Neon")
    p_desc.add_argument("--table", required=True, help="Nombre de la tabla")
    p_desc.set_defaults(func=cmd_describe)

    p_sync = sub.add_parser("sync", help="Sincronizar (upsert) tablas de Neon hacia tu Postgres local")
    p_sync.add_argument("--neon", required=True, help="Connection string de Neon (solo lectura)")
    p_sync.add_argument("--local", required=True, help="Connection string de tu Postgres local")
    p_sync.add_argument("--table", required=True, action="append", help="Tabla a sincronizar (repetible)")
    p_sync.add_argument("--batch-size", type=int, default=500, help="Filas por lote (default: 500)")
    p_sync.set_defaults(func=cmd_sync)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
