#!/usr/bin/env python3
"""
Script para importar TDAs e TRTs do Excel oficial da Rodonaves
Arquivo: TDAs e TRTs 2025 11_04_25 - NXT.xlsx
"""

import pandas as pd
from sqlmodel import Session, select
from frete_app.db import engine, create_db_and_tables
from frete_app.models_extended import (
    CidadeRodonaves, TaxaEspecial, HistoricoImportacao
)
from datetime import datetime
import re


def extrair_valor_taxa(texto: str) -> tuple[float, str]:
    """
    Extrai valor e tipo da taxa de um texto
    Retorna (valor, tipo) onde tipo é 'FIXO' ou 'PERCENTUAL'
    """
    if not texto or pd.isna(texto):
        return (None, None)

    texto = str(texto).strip().upper()

    # Remover R$ e espaços
    texto = texto.replace('R$', '').replace('R', '').replace(' ', '')

    # Verificar se é percentual
    if '%' in texto:
        try:
            valor = float(texto.replace('%', '').replace(',', '.'))
            return (valor / 100, 'PERCENTUAL')  # Converter para decimal
        except:
            return (None, None)

    # Tentar extrair valor fixo
    try:
        # Substituir vírgula por ponto
        texto = texto.replace(',', '.')
        # Pegar apenas números e ponto
        match = re.search(r'[\d.]+', texto)
        if match:
            valor = float(match.group())
            return (valor, 'FIXO')
    except:
        pass

    return (None, None)


def normalizar_nome_cidade(nome: str) -> str:
    """
    Normaliza nome da cidade para matching
    """
    if not nome:
        return ""

    nome = nome.strip().upper()

    # Remover acentos comuns
    substituicoes = {
        'Á': 'A', 'À': 'A', 'Ã': 'A', 'Â': 'A',
        'É': 'E', 'È': 'E', 'Ê': 'E',
        'Í': 'I', 'Ì': 'I', 'Î': 'I',
        'Ó': 'O', 'Ò': 'O', 'Õ': 'O', 'Ô': 'O',
        'Ú': 'U', 'Ù': 'U', 'Û': 'U',
        'Ç': 'C'
    }

    for old, new in substituicoes.items():
        nome = nome.replace(old, new)

    return nome


def importar_taxas(excel_path: str):
    """
    Importa TDAs e TRTs do Excel para o banco de dados
    """
    print(f"Lendo arquivo Excel: {excel_path}")

    # Tentar ler o Excel
    try:
        # Ler todas as abas
        xl_file = pd.ExcelFile(excel_path)
        print(f"Abas encontradas: {xl_file.sheet_names}")

        # Procurar aba com TDA/TRT
        df = None
        for sheet_name in xl_file.sheet_names:
            if any(x in sheet_name.upper() for x in ['TDA', 'TRT', 'TAXA']):
                df = pd.read_excel(excel_path, sheet_name=sheet_name)
                print(f"Usando aba: {sheet_name}")
                break

        if df is None:
            # Usar primeira aba
            df = pd.read_excel(excel_path, sheet_name=0)
            print(f"Usando primeira aba")

    except Exception as e:
        print(f"Erro ao ler Excel: {e}")
        return

    print(f"Total de {len(df)} linhas encontradas")

    # Limpar nomes das colunas
    df.columns = df.columns.str.strip()

    with Session(engine) as session:
        # Estatísticas
        stats = {
            'tdas': 0,
            'trts': 0,
            'cidades_nao_encontradas': [],
            'erros': []
        }

        # Cache de cidades
        cidades_cache = {}

        # Processar cada linha
        for idx, row in df.iterrows():
            try:
                # Extrair dados usando nomes corretos das colunas
                uf = str(row.get('UF', '')).strip().upper()
                cidade_nome = str(row.get('CIDADE', '')).strip()
                valor = row.get('VALOR', 0)
                tarifa_descricao = str(row.get('TARIFA', '')).strip().upper()

                # Determinar se é TDA ou TRT pela descrição da tarifa
                tda_valor = None
                trt_valor = None
                observacao = tarifa_descricao

                if any(keyword in tarifa_descricao for keyword in ['RISCO', 'DIFICULDADE', 'ACESSO']):
                    tda_valor = valor  # Taxa de Dificuldade de Acesso/Risco
                elif any(keyword in tarifa_descricao for keyword in ['RESTRICAO', 'DESPACHO', 'CIDADE']):
                    trt_valor = valor  # Taxa de Restrição de Trânsito
                else:
                    # Se não conseguir identificar, assumir como TDA
                    tda_valor = valor

                # Validar dados mínimos
                if not uf or not cidade_nome:
                    continue

                # Pular cabeçalhos duplicados
                if uf == 'UF':
                    continue

                # Normalizar nome da cidade
                cidade_normalizada = normalizar_nome_cidade(cidade_nome)

                # Buscar cidade no cache ou banco
                cache_key = f"{uf}_{cidade_normalizada}"
                if cache_key in cidades_cache:
                    cidade = cidades_cache[cache_key]
                else:
                    # Buscar no banco
                    cidade = session.exec(
                        select(CidadeRodonaves).join(
                            CidadeRodonaves.estado
                        ).where(
                            CidadeRodonaves.nome == cidade_normalizada,
                            CidadeRodonaves.estado.has(sigla=uf)
                        )
                    ).first()

                    if not cidade:
                        # Tentar busca parcial
                        cidades = session.exec(
                            select(CidadeRodonaves).join(
                                CidadeRodonaves.estado
                            ).where(
                                CidadeRodonaves.nome.contains(cidade_normalizada[:10]),
                                CidadeRodonaves.estado.has(sigla=uf)
                            )
                        ).all()

                        if cidades:
                            # Pegar a melhor correspondência
                            for c in cidades:
                                if cidade_normalizada in c.nome:
                                    cidade = c
                                    break

                    if cidade:
                        cidades_cache[cache_key] = cidade

                if not cidade:
                    stats['cidades_nao_encontradas'].append(f"{cidade_nome}/{uf}")
                    continue

                # Processar TDA
                tda_val, tda_tipo = extrair_valor_taxa(tda_valor)

                # Processar TRT
                trt_val, trt_tipo = extrair_valor_taxa(trt_valor)

                # Se não tem nenhuma taxa válida, pular
                if not tda_val and not trt_val:
                    continue

                # Verificar se já existe taxa para esta cidade
                taxa_existente = session.exec(
                    select(TaxaEspecial).where(
                        TaxaEspecial.cidade_id == cidade.id
                    )
                ).first()

                if taxa_existente:
                    # Atualizar taxa existente
                    if tda_val:
                        taxa_existente.valor_tda = tda_val
                        taxa_existente.tipo_tda = tda_tipo
                    if trt_val:
                        taxa_existente.valor_trt = trt_val
                        taxa_existente.tipo_trt = trt_tipo

                    if observacao:
                        taxa_existente.descricao = observacao

                else:
                    # Criar nova taxa
                    tipo_taxa = "AMBAS" if tda_val and trt_val else ("TDA" if tda_val else "TRT")

                    # Extrair justificativa da observação
                    justificativa = None
                    if observacao:
                        obs_upper = observacao.upper()
                        if 'RISCO' in obs_upper:
                            justificativa = 'Zona de risco'
                        elif any(x in obs_upper for x in ['RESTRICAO', 'RESTRIÇÃO']):
                            justificativa = 'Restrição municipal'
                        elif 'DIFICIL' in obs_upper or 'DIFÍCIL' in obs_upper:
                            justificativa = 'Dificuldade de acesso'
                        elif 'TRANSITO' in obs_upper or 'TRÂNSITO' in obs_upper:
                            justificativa = 'Restrição de trânsito'

                    taxa = TaxaEspecial(
                        cidade_id=cidade.id,
                        tipo_taxa=tipo_taxa,
                        valor_tda=tda_val,
                        tipo_tda=tda_tipo,
                        valor_trt=trt_val,
                        tipo_trt=trt_tipo,
                        descricao=observacao if observacao else None,
                        justificativa=justificativa
                    )
                    session.add(taxa)

                # Atualizar flags na cidade
                if tda_val:
                    cidade.tem_tda = True
                    stats['tdas'] += 1
                if trt_val:
                    cidade.tem_trt = True
                    stats['trts'] += 1

                # Commit a cada 50 taxas
                if (stats['tdas'] + stats['trts']) % 50 == 0:
                    session.commit()
                    print(f"{stats['tdas']} TDAs e {stats['trts']} TRTs importadas...")

            except Exception as e:
                error_msg = f"Erro na linha {idx + 1}: {str(e)}"
                stats['erros'].append(error_msg)
                print(f"Erro: {error_msg}")
                continue

        # Commit final
        session.commit()

        # Criar registro de importação
        historico = HistoricoImportacao(
            tipo_arquivo="EXCEL_TAXAS",
            nome_arquivo=excel_path.split('\\')[-1],
            total_registros=len(df),
            registros_importados=stats['tdas'] + stats['trts'],
            registros_atualizados=0,
            registros_erro=len(stats['erros']),
            status="SUCESSO" if len(stats['erros']) == 0 else "PARCIAL",
            mensagem_erro="; ".join(stats['erros'][:5]) if stats['erros'] else None
        )
        session.add(historico)
        session.commit()

        # Relatório final
        print("\n" + "="*50)
        print("RELATORIO DE IMPORTACAO DE TAXAS")
        print("="*50)
        print(f"TDAs importadas: {stats['tdas']}")
        print(f"TRTs importadas: {stats['trts']}")
        print(f"Total de taxas: {stats['tdas'] + stats['trts']}")

        if stats['cidades_nao_encontradas']:
            print(f"\nCidades nao encontradas: {len(stats['cidades_nao_encontradas'])}")
            # Mostrar apenas as primeiras 10
            for cidade in stats['cidades_nao_encontradas'][:10]:
                print(f"   - {cidade}")
            if len(stats['cidades_nao_encontradas']) > 10:
                print(f"   ... e mais {len(stats['cidades_nao_encontradas']) - 10} cidades")

        if stats['erros']:
            print(f"\nErros: {len(stats['erros'])}")
            for erro in stats['erros'][:5]:
                print(f"   - {erro}")

        print("="*50)


def verificar_taxas_importadas():
    """
    Verifica e exibe estatísticas das taxas importadas
    """
    with Session(engine) as session:
        # Total de taxas
        total_taxas = session.exec(select(TaxaEspecial)).all()
        print(f"\nTotal de taxas no banco: {len(total_taxas)}")

        # Por tipo
        tdas = [t for t in total_taxas if t.valor_tda]
        trts = [t for t in total_taxas if t.valor_trt]
        ambas = [t for t in total_taxas if t.valor_tda and t.valor_trt]

        print(f"   - Apenas TDA: {len(tdas) - len(ambas)}")
        print(f"   - Apenas TRT: {len(trts) - len(ambas)}")
        print(f"   - TDA e TRT: {len(ambas)}")

        # Por tipo de cobrança
        fixas = [t for t in total_taxas if t.tipo_tda == 'FIXO' or t.tipo_trt == 'FIXO']
        percentuais = [t for t in total_taxas if t.tipo_tda == 'PERCENTUAL' or t.tipo_trt == 'PERCENTUAL']

        print(f"\nPor tipo de cobranca:")
        print(f"   - Valor fixo: {len(fixas)}")
        print(f"   - Percentual: {len(percentuais)}")

        # Exemplos
        print("\n📝 Exemplos de taxas:")
        for taxa in total_taxas[:5]:
            cidade = taxa.cidade
            estado = cidade.estado
            print(f"\n   {cidade.nome}/{estado.sigla}:")
            if taxa.valor_tda:
                if taxa.tipo_tda == 'FIXO':
                    print(f"      TDA: R$ {taxa.valor_tda:.2f}")
                else:
                    print(f"      TDA: {taxa.valor_tda * 100:.2f}%")
            if taxa.valor_trt:
                if taxa.tipo_trt == 'FIXO':
                    print(f"      TRT: R$ {taxa.valor_trt:.2f}")
                else:
                    print(f"      TRT: {taxa.valor_trt * 100:.2f}%")
            if taxa.justificativa:
                print(f"      Justificativa: {taxa.justificativa}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        excel_path = sys.argv[1]
    else:
        # Caminho padrão
        excel_path = r"C:\Users\Beto\Dropbox\NXT\Dev\fretes-rodonaves\TDAs e TRTs 2025 11_04_25 - NXT.xlsx"

    print("Iniciando importacao de TDAs e TRTs")
    print(f"Arquivo: {excel_path}")

    # Importar taxas
    importar_taxas(excel_path)

    # Verificar importação
    verificar_taxas_importadas()

    print("\nImportacao completa!")