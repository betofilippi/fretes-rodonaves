#!/usr/bin/env python3
"""
Script para importar prazos de entrega CPF do Excel
Lê a tabela "Relação Cidades Atendidas Modal Rodoviário_25_03_25.xlsx"
e atualiza o banco com prazos mínimo e máximo para CPF
"""

import pandas as pd
import unicodedata
from sqlmodel import Session, select, update
from frete_app.db import engine
from frete_app.models_extended import CidadeRodonaves
from typing import Dict, List, Tuple
import sys
from pathlib import Path

# Configuração
EXCEL_FILE = r"C:\Users\Beto\Dropbox\NXT\Dev\fretes-rodonaves\Relação Cidades Atendidas Modal Rodoviário_25_03_25.xlsx"

def normalize_text(text: str) -> str:
    """Remove acentos e normaliza texto para comparação"""
    if pd.isna(text):
        return ""
    text = str(text).upper().strip()
    # Remove acentos
    nfkd = unicodedata.normalize('NFKD', text)
    text_sem_acento = "".join([c for c in nfkd if not unicodedata.combining(c)])
    return text_sem_acento

def carregar_dados_excel():
    """Carrega e prepara dados do Excel"""
    print(f"Lendo arquivo Excel: {EXCEL_FILE}")

    try:
        # Ler Excel com header na linha 4 (índice 3)
        df = pd.read_excel(EXCEL_FILE, header=3, engine='openpyxl')

        # Renomear colunas pelo índice para evitar problemas com caracteres especiais
        column_mapping = {
            df.columns[7]: 'municipio_destino',    # Municipio_Destino
            df.columns[6]: 'uf_destino',           # UF_dest
            df.columns[4]: 'categoria',            # CAPITAL / INTERIOR
            df.columns[15]: 'prazo_min_cpf',       # Prazo Mínimo CPF (column 15)
            df.columns[16]: 'prazo_max_cpf',       # Prazo Máximo CPF (column 16)
            df.columns[10]: 'distancia_und_municipio'  # Distância Und e Município Dest
        }

        df = df.rename(columns=column_mapping)

        # Filtrar apenas colunas necessárias
        df = df[['municipio_destino', 'uf_destino', 'categoria',
                 'prazo_min_cpf', 'prazo_max_cpf', 'distancia_und_municipio']]

        # Remover linhas sem cidade
        df = df.dropna(subset=['municipio_destino'])

        # Normalizar nomes de cidades
        df['municipio_normalizado'] = df['municipio_destino'].apply(normalize_text)
        df['uf_destino'] = df['uf_destino'].apply(lambda x: str(x).upper().strip() if pd.notna(x) else '')

        # Identificar tipo de transporte baseado na categoria
        df['tipo_transporte'] = df['categoria'].apply(
            lambda x: 'FLUVIAL' if pd.notna(x) and 'FLUVIAL' in str(x).upper() else 'RODOVIARIO'
        )

        # Converter prazos para inteiros
        df['prazo_min_cpf'] = pd.to_numeric(df['prazo_min_cpf'], errors='coerce').fillna(0).astype(int)
        df['prazo_max_cpf'] = pd.to_numeric(df['prazo_max_cpf'], errors='coerce').fillna(0).astype(int)

        print(f"Total de registros carregados: {len(df)}")
        print(f"Estados encontrados: {df['uf_destino'].nunique()}")
        print(f"Cidades com prazos CPF: {df[(df['prazo_min_cpf'] > 0) & (df['prazo_max_cpf'] > 0)].shape[0]}")

        # Agrupar por cidade+UF pegando o menor prazo (caso haja duplicatas)
        df_agrupado = df.groupby(['municipio_normalizado', 'uf_destino']).agg({
            'prazo_min_cpf': 'min',
            'prazo_max_cpf': 'min',
            'tipo_transporte': 'first',
            'municipio_destino': 'first'
        }).reset_index()

        print(f"Cidades únicas após agrupamento: {len(df_agrupado)}")

        return df_agrupado

    except Exception as e:
        print(f"Erro ao ler arquivo Excel: {e}")
        return None

def atualizar_banco_dados(df_prazos):
    """Atualiza o banco de dados com os prazos de entrega"""

    with Session(engine) as session:
        # Buscar todas as cidades do banco
        cidades_db = session.exec(select(CidadeRodonaves)).all()

        # Criar dicionário para busca rápida
        cidades_dict = {}
        for cidade in cidades_db:
            chave = f"{normalize_text(cidade.nome)}_{cidade.estado.sigla}"
            cidades_dict[chave] = cidade

        # Contadores
        atualizadas = 0
        nao_encontradas = []
        cidades_fluviais = 0

        print("\nAtualizando prazos de entrega no banco de dados...")

        # Processar cada cidade do Excel
        for _, row in df_prazos.iterrows():
            if row['prazo_min_cpf'] <= 0 or row['prazo_max_cpf'] <= 0:
                continue

            chave = f"{row['municipio_normalizado']}_{row['uf_destino']}"

            if chave in cidades_dict:
                cidade = cidades_dict[chave]

                # Atualizar campos de prazo
                cidade.prazo_cpf_min_dias = int(row['prazo_min_cpf'])
                cidade.prazo_cpf_max_dias = int(row['prazo_max_cpf'])
                cidade.tipo_transporte = row['tipo_transporte']

                # Manter compatibilidade com campo antigo (usar média)
                cidade.prazo_entrega_dias = int((row['prazo_min_cpf'] + row['prazo_max_cpf']) / 2)

                if row['tipo_transporte'] == 'FLUVIAL':
                    cidades_fluviais += 1

                atualizadas += 1

                if atualizadas % 100 == 0:
                    print(f"  {atualizadas} cidades atualizadas...")
            else:
                nao_encontradas.append(f"{row['municipio_destino']}/{row['uf_destino']}")

        # Commit das alterações
        session.commit()

        print(f"\n[OK] Importação concluída!")
        print(f"  Total de cidades atualizadas: {atualizadas}")
        print(f"  Cidades fluviais identificadas: {cidades_fluviais}")
        print(f"  Cidades não encontradas no banco: {len(nao_encontradas)}")

        if len(nao_encontradas) > 0 and len(nao_encontradas) <= 20:
            print("\n  Cidades não encontradas (primeiras 20):")
            for cidade in nao_encontradas[:20]:
                print(f"    - {cidade}")

        # Mostrar algumas amostras
        print("\n[INFO] Exemplos de prazos importados:")
        exemplos = session.exec(
            select(CidadeRodonaves)
            .where(CidadeRodonaves.prazo_cpf_min_dias.is_not(None))
            .limit(10)
        ).all()

        for cidade in exemplos:
            tipo = f" ({cidade.tipo_transporte})" if cidade.tipo_transporte == 'FLUVIAL' else ""
            print(f"  {cidade.nome}/{cidade.estado.sigla}: {cidade.prazo_cpf_min_dias} a {cidade.prazo_cpf_max_dias} dias{tipo}")

        # Estatísticas finais
        total_com_prazo = session.exec(
            select(CidadeRodonaves).where(CidadeRodonaves.prazo_cpf_min_dias.is_not(None))
        ).all()

        total_fluvial = session.exec(
            select(CidadeRodonaves).where(CidadeRodonaves.tipo_transporte == 'FLUVIAL')
        ).all()

        print(f"\n[STATS] Estatísticas do banco:")
        print(f"  Total de cidades com prazo CPF: {len(total_com_prazo)}")
        print(f"  Total de cidades fluviais: {len(total_fluvial)}")

        return atualizadas

def verificar_cidades_importantes():
    """Verifica se cidades importantes foram atualizadas corretamente"""

    print("\n[VERIFY] Verificando cidades importantes...")

    cidades_teste = [
        ("SAO PAULO", "SP", 4, 6),
        ("BALNEARIO CAMBORIU", "SC", 6, 8),
        ("PONTA GROSSA", "PR", 4, 6),
        ("BRASILIA", "DF", 6, 8),
        ("CAMPINAS", "SP", 4, 6)
    ]

    with Session(engine) as session:
        for nome, uf, min_esperado, max_esperado in cidades_teste:
            cidade = session.exec(
                select(CidadeRodonaves)
                .where(CidadeRodonaves.nome == nome)
                .where(CidadeRodonaves.estado.has(sigla=uf))
            ).first()

            if cidade and cidade.prazo_cpf_min_dias:
                status = "[OK]" if cidade.prazo_cpf_min_dias == min_esperado else "[WARN]"
                print(f"  {status} {nome}/{uf}: {cidade.prazo_cpf_min_dias} a {cidade.prazo_cpf_max_dias} dias")
                if cidade.tipo_transporte == "FLUVIAL":
                    print(f"      (Transporte Fluvial)")
            else:
                print(f"  [ERR] {nome}/{uf}: Sem dados de prazo")

def main():
    """Função principal"""

    print("=" * 60)
    print("IMPORTAÇÃO DE PRAZOS DE ENTREGA CPF")
    print("=" * 60)

    # Verificar se o arquivo existe
    if not Path(EXCEL_FILE).exists():
        print(f"[ERROR] Erro: Arquivo Excel não encontrado: {EXCEL_FILE}")
        return 1

    # Carregar dados do Excel
    df_prazos = carregar_dados_excel()

    if df_prazos is None or df_prazos.empty:
        print("[ERROR] Erro: Não foi possível carregar dados do Excel")
        return 1

    # Atualizar banco de dados
    total_atualizadas = atualizar_banco_dados(df_prazos)

    if total_atualizadas > 0:
        # Verificar cidades importantes
        verificar_cidades_importantes()

        print("\n[SUCCESS] Importação de prazos de entrega CPF concluída com sucesso!")
        print(f"   {total_atualizadas} cidades atualizadas com prazos de entrega")
        return 0
    else:
        print("\n[WARNING] Nenhuma cidade foi atualizada")
        return 1

if __name__ == "__main__":
    sys.exit(main())