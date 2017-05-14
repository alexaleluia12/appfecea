

import re
import datetime
# import rlcompleter
# import readline
# readline.parse_and_bind('tab: complete')

import requests
import bs4

import utils

# formato url imagens feed
# http://www.fecea.br/userfiles/banner/bannerfans_19132458.jpg
# userfiles* vem da imagem

url_feed = "http://www.fecea.br/"
url_eventos = "http://www.fecea.br/cursos/"


def extrari_inscricao(inscricao_full):
    """
    inscricao_full like "18/04/2017 até 07/05/2017"

    Retorna {"inicio_inscricao": v1, "fim_inscricao": v2}
    data formato YYYY-mm-dd
    """
    lst = inscricao_full.split(" ")
    primeiro = lst[0]
    ultimo = lst[-1]
    saida = {"inicio_inscricao": None, "fim_inscricao": None}

    saida["inicio_inscricao"] = "-".join(primeiro.split('/')[::-1])
    saida["fim_inscricao"] = "-".join(ultimo.split('/')[::-1])
    return saida


def preenche_vazio(conn, lst, template, sql_topo):
    for i in lst:
        meio_sql = template.format(*i)
        sql = sql_topo + meio_sql
        conn.execute(sql)


def excluir(conn, lst, tabela):
    template = 'DELETE FROM `{}` WHERE `id` in ({})'
    ids = [str(i[0]) for i in lst]

    preids =  ", ".join(ids)
    sql = template.format(tabela, preids)
    conn.execute(sql)


def preenche_evento():
    """
    Busca no site e atualiza a tabela de eventos
    """
    resposta = requests.get(url_eventos)

    lst_saida = []
    ir = False
    if resposta.ok:
        ir = True
        parse = bs4.BeautifulSoup(resposta.text, 'html.parser')
        lst = parse.find_all("table")
        filtro = []
        inome = 0
        iinscricao = 2
        ivagas = 3
        agora = datetime.datetime.now().strftime(utils.foramto_full_db)
        for i in lst:
            tmp = i.get("class")
            if tmp and "bordas" in tmp:
                filtro.append(i)

        if len(filtro) > 0:
            alvo = filtro[0]
            lst_linha = alvo.find_all('tr')[2:]
            for j in lst_linha:
                lst_coluna = j.find_all('td')
                nome = inicio_inscricao = fim_inscricao = link = ""
                k = lst_coluna[inome]
                nome = k.font.a.get_text().strip()
                link = url_eventos + k.font.a.get('href').strip()

                k = lst_coluna[iinscricao]
                inscricao = k.font.get_text().strip()
                dinscricao = extrari_inscricao(inscricao)
                inicio_inscricao = dinscricao["inicio_inscricao"]
                fim_inscricao = dinscricao["fim_inscricao"]

                k = lst_coluna[ivagas]
                vagas = k.span.font.get_text().strip()

                lst_saida.append(["NULL", agora, nome, inicio_inscricao,
                                  fim_inscricao, link, vagas])
    else:
        print("pagina forma do ar")
        return

    template = "({}, '{}', '{}', '{}', '{}', '{}', {});"
    if ir:
        print("-- evento")
        conn = utils.get_db_conn()
        lst_pagina = sorted(lst_saida, key=lambda elemento: elemento[2])
        nomes_pagina = [i[2] for i in lst_pagina]
        try:
            with conn.cursor() as cursor:
                sql_vazio = "SELECT count(*) FROM `evento`"
                if utils.is_empty(cursor, sql_vazio):
                    sql_inserir = "INSERT INTO `evento` VALUES "
                    preenche_vazio(cursor, lst_saida, template, sql_inserir)
                else:
                    # atulizacao, dados ja existem
                    sql_todos = "SELECT * FROM `evento` ORDER BY `nome`"
                    nome_todos = "SELECT `nome` FROM `evento` ORDER BY `nome`"
                    lst_nome_todos = utils.get_all(cursor, nome_todos)
                    lst_nome_todos = [i[0] for i in lst_nome_todos]
                    lst_todos = utils.get_all(cursor, sql_todos)

                    # atualizar
                    lst_atualizar = []
                    lst_inserir = []
                    for k in lst_pagina:
                        # print(repr(k[2]))
                        if k[2] in lst_nome_todos:
                            lst_atualizar.append(k)
                        else:
                            lst_inserir.append(k)

                    # remover
                    lst_remover = []
                    for k1 in lst_todos:
                        if k1[2] not in nomes_pagina:
                            lst_remover.append(k1)

                    if len(lst_remover):
                        print("exlui", len(lst_remover))
                        excluir(cursor, lst_remover, 'evento')
                        conn.commit()
                        lst_todos = utils.get_all(cursor, sql_todos)

                    # datas e vagas
                    lst_nomes = [g[2] for g in lst_todos]
                    chaves = {g[2]: g[0] for g in lst_todos}

                    if len(lst_atualizar):  # elementos que vem da pagina
                        sql = "UPDATE `evento` SET `inicio_inscricao`='{}'" + \
                            ", `fim_inscricao`='{}', `link`='{}',`vagas`={}" +\
                            " WHERE `id`={}"

                        print("atualiza", len(lst_atualizar))
                        for i in lst_atualizar:
                            tmp_lst = i[3:] + [chaves[i[2]]]
                            sql_completo = sql.format(*tmp_lst)
                            # print(sql_completo)
                            cursor.execute(sql_completo)

                    if len(lst_inserir):
                        print("novos", len(lst_inserir))
                        sql_inserir = "INSERT INTO `evento` VALUES "
                        preenche_vazio(cursor, lst_inserir, template, sql_inserir)


                    """
                    meu proprio controle:
                        remover eventos que nao tem vaga, ou terminou a data de inscricao
                    casos especiais:
                        A evento novo na pagina
                        B evento nao existe mais na pagina
                    *. trazer os eventos ordenas por nome. (ordernar os eventos aqui tmb)
                    (essa parte vai ser igual ao do feed)
                    A.  not (nome in lst_nomes) => elemento novo
                    B.  banco = banco[:len(pagina)] # oque sobra do tamanho da pagina eh pq foi removido


                    1. controle da pagina
                    2. meu controle

                    """
            conn.commit()

        finally:
            conn.close()


def preenche_feed():
    """Feito para buscar dados do feed. Lida com dados antigos

    caso um elemento ja exista na pagina ele nao é atualizado
    """
    resposta = requests.get(url_feed)

    lst_saida = []
    ir = False
    if resposta.ok:  # extrai o conteudo da pagina
        ir = True
        parse = bs4.BeautifulSoup(resposta.text, 'html.parser')
        # /html/body/div/div/div[2]/div[2]/div/ul/li[] xpath
        div_principal = parse.find(id="main-area-1")
        filhos = div_principal.children
        alvo = None
        for i in filhos:
            if i.name == "ul":
                alvo = i
                break
        lst_img = alvo.find_all('img')
        agora = datetime.datetime.now().strftime(utils.foramto_full_db)
        for k in lst_img:
            texto = k.get('alt')
            link_img = url_feed + k.get('src')
            link = k.parent.get('href')  # pode nao existir
            link = link if link else "NULL"
            lst_saida.append(["NULL", agora, texto, link_img, link])
    else:
        print("pagina fora do ar")
        return

    conn = None
    template = "({}, '{}', '{}', '{}', '{}');"
    if ir:
        print("-- feed")
        conn = utils.get_db_conn()
        lst_pagina = lst_saida
        nomes_pagina = [i[2] for i in lst_pagina]
        try:
            with conn.cursor() as cursor:

                sql_vazio = "SELECT count(*) FROM `feed`"
                if utils.is_empty(cursor, sql_vazio):
                    sql_inserir = "INSERT INTO `feed` VALUES "
                    preenche_vazio(cursor, lst_saida, template, sql_inserir)
                else:
                    # atulizacao, dados ja existem
                    sql_todos = "SELECT * FROM `feed` ORDER BY `texto`"
                    nome_todos = "SELECT `texto` FROM `feed` ORDER BY `texto`"
                    lst_nome_todos = utils.get_all(cursor, nome_todos)
                    lst_nome_todos = [i[0] for i in lst_nome_todos]
                    lst_todos = utils.get_all(cursor, sql_todos)

                    # apenas insere ou exclui nao atualiza
                    lst_inserir = []
                    for k in lst_pagina:
                        # print(repr(k[2]))
                        if k[2] not in lst_nome_todos:
                            lst_inserir.append(k)

                    # remover
                    lst_remover = []
                    for k1 in lst_todos:
                        if k1[2] not in nomes_pagina:
                            lst_remover.append(k1)

                    if len(lst_remover):
                        print("exlui", len(lst_remover))
                        excluir(cursor, lst_remover, 'feed')
                        conn.commit()
                        lst_todos = utils.get_all(cursor, sql_todos)


                    if len(lst_inserir):
                        print("novos", len(lst_inserir))
                        sql_inserir = "INSERT INTO `feed` VALUES "
                        preenche_vazio(cursor, lst_inserir, template, sql_inserir)

            conn.commit()

        finally:
            conn.close()

if __name__ == '__main__':
    preenche_feed()
    preenche_evento()
