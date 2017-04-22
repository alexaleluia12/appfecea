

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


def preenche_evento():
    """

    TODO
    atualizar os eventos
    """
    resposta = requests.get(url_eventos)

    lst_saida = []
    if resposta.ok:
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

    template = "({}, '{}', '{}', '{}', '{}', '{}', {});"
    if len(lst_saida) > 0:
        conn = utils.get_db_conn()
        try:
            with conn.cursor() as cursor:
                top_sql = "INSERT INTO `evento` VALUES "
                for i in lst_saida:
                    meio_sql = template.format(*i)
                    sql = top_sql + meio_sql
                    cursor.execute(sql)
            conn.commit()

        finally:
            conn.close()


def preenche_feed():
    """Feito para buscar dados do feed. Lida com dados antigos

    TODO:
    atualizacao do feed
    """
    resposta = requests.get(url_feed)

    lst_saida = []
    if resposta.ok:  # extrai o conteudo da pagina
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

    conn = None
    template = "({}, '{}', '{}', '{}', '{}');"
    if len(lst_saida):
        conn = utils.get_db_conn()
        try:
            with conn.cursor() as cursor:
                top_sql = "INSERT INTO `feed` VALUES "
                for i in lst_saida:
                    meio_sql = template.format(*i)
                    sql = top_sql + meio_sql
                    cursor.execute(sql)
            conn.commit()

        finally:
            conn.close()



if __name__ == '__main__':
    preenche_evento()
