
import json
import re

import pymysql


formato_br = "%d/%m/%Y"
formato_us = "%Y-%m-%d"
formato_full = "[%Y-%m-%d %H:%M:%S]"
foramto_full_db = "%Y-%m-%d %H:%M:%S"
banco_nome = 'banco-dev'


def get_config(file_name):
    """
    Dicionario com as chave valor do arquivo
    """
    resultado = None
    with open(file_name + ".json") as f:
        resultado = json.load(f)

    return resultado


def get_db_conn():
    dbconf = get_config(banco_nome)

    conn = pymysql.connect(
        host=dbconf['host'], user=dbconf['user'], password=dbconf['password'],
        db=dbconf['database']
    )
    return conn


def is_empty(conn, sql):
    conn.execute(sql)
    resp = conn.fetchone()
    return resp[0] == 0


def get_all(conn, sql):
    conn.execute(sql)
    return conn.fetchall()


def get_datas():
    """
    Retorna (data-inicio, data-fim)
    datas estao em datetime
    """
    conn = get_db_conn()
    resultado = None
    try:
        sql = "SELECT data_inicio, data_fim from `botserasa` LIMIT 1;"
        with conn.cursor() as cursor:
            cursor.execute(sql)
            resultado = cursor.fetchone()
    finally:
        conn.close()

    return resultado


def set_datas(data_inicio, data_fim):
    """
    Salvas as datas no banco
    data_inicio: str, data_fim: str
    devem estar no formato YYYY-mm-dd
    """
    padrao_data = "^\d{4}-\d{2}-\d{2}$"
    for e in [data_inicio, data_fim]:
        if not re.match(padrao_data, e):
            raise Exception("Formato da data esta incorreto para " + e +
                            ". Se espera YYYY-mm-dd")
    conn = get_db_conn()
    # da um update aqui
    try:
        sql = "UPDATE `botserasa` SET `data_inicio` = %s, `data_fim` = %s WHERE `id` = %s"
        with conn.cursor() as cursor:
            cursor.execute(sql, (data_inicio, data_fim, 1))

        conn.commit()
    finally:
        conn.close()
