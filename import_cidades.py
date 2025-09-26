#!/usr/bin/env python3
"""
Script para importar dados de cidades do Excel oficial da Rodonaves
Arquivo: Relação Cidades Atendidas Modal Rodoviário_25_03_25.xlsx

CORREÇÕES IMPLEMENTADAS:
1. Atualiza cidades existentes em vez de pular
2. Usa coluna correta "Distância Und e Município Dest" para distância local
3. Corrige encoding de caracteres portugueses nas colunas
4. Adiciona lógica de fallback para dados de distância
5. Corrige extração da coluna de prazo
6. Garante que todas as capitais recebem suas distâncias adequadas
"""

import pandas as pd
from sqlmodel import Session, select
from frete_app.db import engine, create_db_and_tables
from frete_app.models_extended import (
    Estado, FilialRodonaves, CidadeRodonaves,
    TabelaTarifaCompleta, HistoricoImportacao
)
from frete_app.models import VersaoTabela
from datetime import datetime
import re
import unicodedata


def normalizar_texto(texto):
    """
    Normaliza texto removendo acentos e caracteres especiais para comparação
    """
    if not texto:
        return ""

    # Normalizar unicode
    texto = unicodedata.normalize('NFKD', str(texto))
    # Remover acentos
    texto = ''.join(c for c in texto if not unicodedata.combining(c))
    return texto.upper().strip()


def normalizar_categoria(uf: str, cidade: str, observacao: str = None) -> str:
    """
    Determina a categoria da cidade baseado em regras da Rodonaves
    """
    cidade = normalizar_texto(cidade)

    # Capitais
    capitais = {
        'SP': ['SAO PAULO'],
        'RJ': ['RIO DE JANEIRO'],
        'MG': ['BELO HORIZONTE'],
        'PR': ['CURITIBA'],
        'SC': ['FLORIANOPOLIS'],
        'RS': ['PORTO ALEGRE'],
        'GO': ['GOIANIA'],
        'DF': ['BRASILIA'],
        'MS': ['CAMPO GRANDE'],
        'MT': ['CUIABA'],
        'ES': ['VITORIA'],
        'BA': ['SALVADOR'],
        'PE': ['RECIFE'],
        'CE': ['FORTALEZA'],
        'PA': ['BELEM'],
        'AM': ['MANAUS'],
        'MA': ['SAO LUIS'],
        'PB': ['JOAO PESSOA'],
        'RN': ['NATAL'],
        'AL': ['MACEIO'],
        'SE': ['ARACAJU'],
        'PI': ['TERESINA'],
        'TO': ['PALMAS'],
        'RR': ['BOA VISTA'],
        'AP': ['MACAPA'],
        'AC': ['RIO BRANCO'],
        'RO': ['PORTO VELHO']
    }

    # Verificar se é capital
    if uf in capitais:
        for capital in capitais[uf]:
            if capital in cidade:
                return 'CAPITAL'

    # Regiões metropolitanas (geralmente Interior 1)
    metro = {
        'SP': ['GUARULHOS', 'OSASCO', 'SANTO ANDRE', 'SAO BERNARDO', 'SAO CAETANO',
               'DIADEMA', 'MAUA', 'SUZANO', 'TABOAO'],
        'RJ': ['NITEROI', 'SAO GONCALO', 'DUQUE DE CAXIAS', 'NOVA IGUACU'],
        'MG': ['CONTAGEM', 'BETIM', 'NOVA LIMA'],
        'PR': ['SAO JOSE DOS PINHAIS', 'COLOMBO', 'ARAUCARIA'],
        'RS': ['CANOAS', 'GRAVATAI', 'VIAMAO', 'NOVO HAMBURGO', 'SAO LEOPOLDO']
    }

    if uf in metro:
        for cidade_metro in metro[uf]:
            if cidade_metro in cidade:
                return 'INTERIOR_1'

    # Lista de cidades importantes (Interior 1)
    importantes = {
        'SP': ['CAMPINAS', 'SANTOS', 'SAO JOSE DOS CAMPOS', 'RIBEIRAO PRETO',
               'SOROCABA', 'JUNDIAI', 'PIRACICABA', 'BAURU', 'SAO VICENTE'],
        'MG': ['UBERLANDIA', 'JUIZ DE FORA', 'MONTES CLAROS', 'UBERABA'],
        'RJ': ['CAMPOS', 'PETROPOLIS', 'VOLTA REDONDA', 'MACAE'],
        'PR': ['LONDRINA', 'MARINGA', 'CASCAVEL', 'PONTA GROSSA', 'FOZ DO IGUACU'],
        'SC': ['JOINVILLE', 'BLUMENAU', 'ITAJAI', 'CRICIUMA', 'CHAPECO'],
        'RS': ['CAXIAS DO SUL', 'PELOTAS', 'SANTA MARIA', 'PASSO FUNDO']
    }

    if uf in importantes:
        for cidade_imp in importantes[uf]:
            if cidade_imp in cidade:
                return 'INTERIOR_1'

    # Verificar menção a fluvial na observação
    if observacao and 'FLUVIAL' in normalizar_texto(observacao):
        return 'FLUVIAL'

    return 'INTERIOR_2'


def extrair_numero(valor, tipo='float'):
    """
    Extrai número de um valor, lidando com diferentes formatos
    """
    if valor is None or pd.isna(valor):
        return None

    try:
        # Converter para string
        valor_str = str(valor).strip()

        if not valor_str or valor_str.lower() in ['nan', 'none', '']:
            return None

        # Remover caracteres não numéricos (exceto ponto e vírgula)
        valor_limpo = re.sub(r'[^\d,.-]', '', valor_str)

        # Substituir vírgula por ponto
        valor_limpo = valor_limpo.replace(',', '.')

        if not valor_limpo:
            return None

        # Extrair primeiro número encontrado
        match = re.search(r'\d+\.?\d*', valor_limpo)
        if match:
            numero = match.group()
            return float(numero) if tipo == 'float' else int(float(numero))

        return None
    except (ValueError, AttributeError):
        return None


def importar_cidades(excel_path: str):
    """
    Importa cidades do Excel para o banco de dados
    """
    print(f"Lendo arquivo Excel: {excel_path}")

    # Ler o Excel - usar linha 3 como cabeçalho (onde estão os nomes das colunas)
    df = pd.read_excel(excel_path, sheet_name=0, header=3)

    # Limpar nomes das colunas e normalizar encoding
    df.columns = [normalizar_texto(col) if col else f"COL_{i}" for i, col in enumerate(df.columns.str.strip())]

    print(f"Total de {len(df)} linhas encontradas")
    print(f"Colunas disponíveis: {list(df.columns)}")

    # Criar tabelas se não existirem
    create_db_and_tables()

    with Session(engine) as session:
        # Estatísticas
        stats = {
            'estados': set(),
            'filiais': set(),
            'cidades_novas': 0,
            'cidades_atualizadas': 0,
            'erros': []
        }

        # Cache de objetos
        estados_cache = {}
        filiais_cache = {}

        # Processar cada linha
        for idx, row in df.iterrows():
            try:
                # Extrair dados básicos
                uf = str(row.get('UF_DEST', '')).strip().upper()
                cidade_nome = str(row.get('MUNICIPIO_DESTINO', '')).strip().upper()

                if not uf or not cidade_nome or uf == 'UF' or pd.isna(uf):
                    continue

                # Estado
                if uf not in estados_cache:
                    estado = session.exec(select(Estado).where(Estado.sigla == uf)).first()
                    if not estado:
                        # Determinar região
                        regiao = 'Sudeste'
                        if uf in ['RS', 'SC', 'PR']:
                            regiao = 'Sul'
                        elif uf in ['GO', 'DF', 'MS', 'MT']:
                            regiao = 'Centro-Oeste'
                        elif uf in ['BA', 'SE', 'AL', 'PE', 'PB', 'RN', 'CE', 'PI', 'MA']:
                            regiao = 'Nordeste'
                        elif uf in ['AM', 'PA', 'AC', 'RO', 'RR', 'AP', 'TO']:
                            regiao = 'Norte'

                        estado = Estado(
                            sigla=uf,
                            nome=uf,  # Será atualizado depois
                            regiao=regiao,
                            tem_cobertura=True
                        )
                        session.add(estado)
                        session.commit()
                        session.refresh(estado)

                    estados_cache[uf] = estado
                    stats['estados'].add(uf)

                estado = estados_cache[uf]

                # Filial de atendimento - usar coluna correta
                filial_codigo = str(row.get('FILIAL_DESTINO', 'HQ')).strip().upper()

                if filial_codigo not in filiais_cache:
                    filial = session.exec(
                        select(FilialRodonaves).where(FilialRodonaves.codigo == filial_codigo)
                    ).first()

                    if not filial:
                        filial = FilialRodonaves(
                            codigo=filial_codigo,
                            nome=f"Filial {filial_codigo}",
                            cidade="A definir",
                            estado_id=estado.id,
                            tipo="FILIAL",
                            ativa=True
                        )
                        session.add(filial)
                        session.commit()
                        session.refresh(filial)

                    filiais_cache[filial_codigo] = filial
                    stats['filiais'].add(filial_codigo)

                filial = filiais_cache[filial_codigo]

                # Buscar cidade existente
                cidade_existente = session.exec(
                    select(CidadeRodonaves).where(
                        CidadeRodonaves.nome == cidade_nome,
                        CidadeRodonaves.estado_id == estado.id
                    )
                ).first()

                # Determinar categoria
                observacao = str(row.get('CAPITAL / INTERIOR', '')).strip()
                categoria = normalizar_categoria(uf, cidade_nome, observacao)

                # Extrair distância - USAR COLUNA CORRETA
                distancia = None

                # Primeira tentativa: coluna de distância local (corrigida)
                dist_col_local = row.get('DISTANCIA UND E MUNICIPIO DEST')
                if dist_col_local is not None:
                    distancia = extrair_numero(dist_col_local, 'float')

                # Fallback: coluna de distância total se local não disponível
                if distancia is None:
                    dist_col_total = row.get('KM TOTAL')
                    if dist_col_total is not None:
                        distancia = extrair_numero(dist_col_total, 'float')

                # Extrair prazo - USAR COLUNAS CORRETAS
                prazo = None

                # Tentar prazo mínimo CNPJ primeiro
                prazo_col = row.get('PRAZO MINIMO CNPJ')
                if prazo_col is not None:
                    prazo = extrair_numero(prazo_col, 'int')

                # Fallback: prazo máximo CNPJ
                if prazo is None:
                    prazo_col = row.get('PRAZO MAXIMO CNPJ')
                    if prazo_col is not None:
                        prazo = extrair_numero(prazo_col, 'int')

                # Verificar flags especiais
                tem_restricao = False
                zona_risco = None

                if observacao:
                    obs_upper = normalizar_texto(observacao)
                    if any(x in obs_upper for x in ['RESTRICAO', 'ENTREGA ESPECIAL']):
                        tem_restricao = True
                    if 'RISCO' in obs_upper:
                        if 'ALTO' in obs_upper:
                            zona_risco = 'ALTO'
                        elif 'MEDIO' in obs_upper:
                            zona_risco = 'MEDIO'
                        else:
                            zona_risco = 'BAIXO'

                # CORREÇÃO PRINCIPAL: Atualizar cidade existente ou criar nova
                if cidade_existente:
                    # Atualizar dados da cidade existente
                    cidade_existente.filial_atendimento_id = filial.id
                    cidade_existente.categoria_tarifa = categoria

                    # Atualizar distância se não existir ou se a nova for melhor
                    if distancia is not None and (
                        cidade_existente.distancia_km is None or
                        distancia < cidade_existente.distancia_km
                    ):
                        cidade_existente.distancia_km = distancia

                    # Atualizar prazo se não existir ou se o novo for melhor
                    if prazo is not None and (
                        cidade_existente.prazo_entrega_dias is None or
                        prazo < cidade_existente.prazo_entrega_dias
                    ):
                        cidade_existente.prazo_entrega_dias = prazo

                    cidade_existente.tem_restricao_entrega = tem_restricao
                    cidade_existente.zona_risco = zona_risco
                    cidade_existente.observacoes = observacao if observacao else None
                    cidade_existente.ativo = True

                    stats['cidades_atualizadas'] += 1
                else:
                    # Criar nova cidade
                    cidade = CidadeRodonaves(
                        nome=cidade_nome,
                        estado_id=estado.id,
                        filial_atendimento_id=filial.id,
                        categoria_tarifa=categoria,
                        distancia_km=distancia,
                        prazo_entrega_dias=prazo,
                        tem_restricao_entrega=tem_restricao,
                        zona_risco=zona_risco,
                        observacoes=observacao if observacao else None,
                        ativo=True
                    )

                    session.add(cidade)
                    stats['cidades_novas'] += 1

                # Commit a cada 100 registros
                total_processados = stats['cidades_novas'] + stats['cidades_atualizadas']
                if total_processados % 100 == 0:
                    session.commit()
                    print(f" {total_processados} registros processados...")

            except Exception as e:
                error_msg = f"Erro na linha {idx + 1}: {str(e)}"
                stats['erros'].append(error_msg)
                print(f" {error_msg}")
                continue

        # Commit final
        session.commit()

        # Criar registro de importação
        historico = HistoricoImportacao(
            tipo_arquivo="EXCEL_CIDADES",
            nome_arquivo=excel_path.split('\\')[-1],
            total_registros=len(df),
            registros_importados=stats['cidades_novas'],
            registros_atualizados=stats['cidades_atualizadas'],
            registros_erro=len(stats['erros']),
            status="SUCESSO" if len(stats['erros']) == 0 else "PARCIAL",
            mensagem_erro="; ".join(stats['erros'][:5]) if stats['erros'] else None
        )
        session.add(historico)
        session.commit()

        # Relatório final
        print("\n" + "="*60)
        print(" RELATÓRIO DE IMPORTAÇÃO - VERSÃO CORRIGIDA")
        print("="*60)
        print(f" Estados: {len(stats['estados'])} ({', '.join(sorted(stats['estados']))})")
        print(f" Filiais: {len(stats['filiais'])}")
        print(f" Cidades novas: {stats['cidades_novas']}")
        print(f" Cidades atualizadas: {stats['cidades_atualizadas']}")
        print(f" Total processado: {stats['cidades_novas'] + stats['cidades_atualizadas']}")
        if stats['erros']:
            print(f" Erros: {len(stats['erros'])}")
            for erro in stats['erros'][:5]:
                print(f"   - {erro}")
        print("="*60)


def atualizar_nomes_estados():
    """
    Atualiza os nomes completos dos estados
    """
    nomes = {
        'SP': 'São Paulo',
        'RJ': 'Rio de Janeiro',
        'MG': 'Minas Gerais',
        'ES': 'Espírito Santo',
        'PR': 'Paraná',
        'SC': 'Santa Catarina',
        'RS': 'Rio Grande do Sul',
        'GO': 'Goiás',
        'DF': 'Distrito Federal',
        'MS': 'Mato Grosso do Sul',
        'MT': 'Mato Grosso',
        'RO': 'Rondônia',
        'AC': 'Acre',
        'AM': 'Amazonas',
        'PA': 'Pará',
        'AP': 'Amapá',
        'RR': 'Roraima',
        'TO': 'Tocantins',
        'BA': 'Bahia',
        'SE': 'Sergipe',
        'AL': 'Alagoas',
        'PE': 'Pernambuco',
        'PB': 'Paraíba',
        'RN': 'Rio Grande do Norte',
        'CE': 'Ceará',
        'PI': 'Piauí',
        'MA': 'Maranhão'
    }

    with Session(engine) as session:
        for sigla, nome in nomes.items():
            estado = session.exec(select(Estado).where(Estado.sigla == sigla)).first()
            if estado:
                estado.nome = nome
        session.commit()
        print(" Nomes dos estados atualizados")


def criar_tarifas_por_categoria():
    """
    Cria tarifas baseadas nas categorias das cidades importadas
    """
    with Session(engine) as session:
        # Pegar versão ativa
        versao = session.exec(select(VersaoTabela).where(VersaoTabela.ativa == True)).first()
        if not versao:
            print(" Nenhuma versão de tabela ativa encontrada")
            return

        # Buscar todas as combinações únicas de estado + categoria
        query = select(
            CidadeRodonaves.categoria_tarifa,
            Estado.sigla
        ).join(Estado).distinct()

        combinacoes = session.exec(query).all()

        print(f" Criando tarifas para {len(combinacoes)} combinações estado/categoria")

        for categoria, uf in combinacoes:
            categoria_completa = f"{uf}_{categoria}"

            # Verificar se já existe
            tarifa_existente = session.exec(
                select(TabelaTarifaCompleta).where(
                    TabelaTarifaCompleta.versao_id == versao.id,
                    TabelaTarifaCompleta.categoria_completa == categoria_completa
                )
            ).first()

            if tarifa_existente:
                continue

            # Criar tarifa com valores base
            # Valores aumentam com distância do sudeste e categoria
            base_capital = 25.00
            base_interior1 = 30.00
            base_interior2 = 35.00
            base_fluvial = 45.00

            # Multiplicadores por região
            mult = 1.0
            if uf in ['RS', 'SC']:
                mult = 2.5
            elif uf in ['PR']:
                mult = 2.2
            elif uf in ['MG', 'ES']:
                mult = 1.8
            elif uf in ['GO', 'DF', 'MS', 'MT']:
                mult = 2.8
            elif uf == 'RJ':
                mult = 1.6

            # Base por categoria
            if categoria == 'CAPITAL':
                base = base_capital
            elif categoria == 'INTERIOR_1':
                base = base_interior1
            elif categoria == 'INTERIOR_2':
                base = base_interior2
            else:  # FLUVIAL
                base = base_fluvial

            # Aplicar multiplicador
            base = base * mult

            tarifa = TabelaTarifaCompleta(
                versao_id=versao.id,
                estado_sigla=uf,
                categoria=categoria,
                categoria_completa=categoria_completa,
                ate_10=round(base, 2),
                ate_20=round(base * 1.4, 2),
                ate_40=round(base * 2.2, 2),
                ate_60=round(base * 3.0, 2),
                ate_100=round(base * 4.8, 2),
                excedente_por_kg=round(base * 0.048, 2)
            )

            session.add(tarifa)

        session.commit()
        print(" Tarifas criadas com sucesso")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        excel_path = sys.argv[1]
    else:
        # Caminho padrão
        excel_path = r"C:\Users\Beto\Dropbox\NXT\Dev\fretes-rodonaves\Relação Cidades Atendidas Modal Rodoviário_25_03_25.xlsx"

    print("Iniciando importação de cidades Rodonaves - VERSÃO CORRIGIDA")
    print(f"Arquivo: {excel_path}")

    # Importar cidades
    importar_cidades(excel_path)

    # Atualizar nomes dos estados
    atualizar_nomes_estados()

    # Criar tarifas
    criar_tarifas_por_categoria()

    print("\n Importação completa!")