#!/usr/bin/env python
"""
Script para importar dados de cidades do TDA/TRT ou usar fallback
"""

import os
import sys
import pandas as pd
from pathlib import Path
from sqlmodel import Session, select

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent))

from frete_app.db import engine
from frete_app.models_extended import Estado, FilialRodonaves, CidadeRodonaves


def import_cities_from_excel():
    """Tenta importar cidades dos arquivos Excel"""

    # Tentar TDA
    tda_file = "TDAs e TRTs 2025 11_04_25 - NXT.xlsx"
    if os.path.exists(tda_file):
        print(f"[INFO] Importando cidades de {tda_file}...")
        try:
            import_tda_data(tda_file)
            return True
        except Exception as e:
            print(f"[ERRO] Falha ao importar TDA: {e}")

    # Tentar arquivo de cidades
    cities_file = "Relação Cidades Atendidas Modal Rodoviário_25_03_25.xlsx"
    if os.path.exists(cities_file):
        print(f"[INFO] Importando cidades de {cities_file}...")
        try:
            import_cities_delivery(cities_file)
            return True
        except Exception as e:
            print(f"[ERRO] Falha ao importar cidades: {e}")

    return False


def import_tda_data(filename):
    """Importa dados TDA do Excel"""
    df = pd.read_excel(filename, sheet_name="TDA Simplificada")

    with Session(engine) as session:
        # Criar filial padrão se não existir
        filial = session.exec(select(FilialRodonaves)).first()
        if not filial:
            filial = FilialRodonaves(codigo=1, nome="SAO PAULO", uf="SP")
            session.add(filial)
            session.commit()
            session.refresh(filial)

        count = 0
        for idx, row in df.iterrows():
            if pd.isna(row.iloc[0]):  # Skip empty rows
                continue

            try:
                cidade = CidadeRodonaves(
                    uf=str(row.iloc[0])[:2].upper(),
                    cidade=str(row.iloc[1]).upper() if not pd.isna(row.iloc[1]) else "",
                    cep_inicial=str(row.iloc[2]) if not pd.isna(row.iloc[2]) else "",
                    cep_final=str(row.iloc[3]) if not pd.isna(row.iloc[3]) else "",
                    filial_id=filial.id,
                    tarifa_minima=float(row.iloc[4]) if not pd.isna(row.iloc[4]) else 50.0,
                    peso_taxado_minimo_kg=10.0,
                    advalorem_percent=0.005
                )
                session.add(cidade)
                count += 1

                if count % 100 == 0:
                    session.commit()
                    print(f"[INFO] {count} cidades importadas...")

            except Exception as e:
                print(f"[AVISO] Erro na linha {idx}: {e}")
                continue

        session.commit()
        print(f"[OK] {count} cidades importadas do TDA")


def import_cities_delivery(filename):
    """Importa cidades com prazos de entrega"""
    df = pd.read_excel(filename, sheet_name=0)

    with Session(engine) as session:
        # Criar filial padrão
        filial = session.exec(select(FilialRodonaves)).first()
        if not filial:
            filial = FilialRodonaves(codigo=1, nome="SAO PAULO", uf="SP")
            session.add(filial)
            session.commit()
            session.refresh(filial)

        count = 0
        for idx, row in df.iterrows():
            if idx < 1:  # Skip header
                continue

            try:
                uf = str(row.iloc[3])[:2].upper()
                cidade_nome = str(row.iloc[2]).upper()

                # Prazos CPF nas colunas 15 e 16
                prazo_min = int(row.iloc[15]) if not pd.isna(row.iloc[15]) else None
                prazo_max = int(row.iloc[16]) if not pd.isna(row.iloc[16]) else None

                cidade = CidadeRodonaves(
                    uf=uf,
                    cidade=cidade_nome,
                    cep_inicial="00000-000",
                    cep_final="99999-999",
                    filial_id=filial.id,
                    tarifa_minima=50.0,
                    peso_taxado_minimo_kg=10.0,
                    advalorem_percent=0.005,
                    prazo_cpf_min_dias=prazo_min,
                    prazo_cpf_max_dias=prazo_max,
                    tipo_transporte="RODOVIARIO"
                )
                session.add(cidade)
                count += 1

                if count % 100 == 0:
                    session.commit()
                    print(f"[INFO] {count} cidades importadas...")

            except Exception as e:
                continue

        session.commit()
        print(f"[OK] {count} cidades importadas com prazos")


def create_essential_cities():
    """Cria conjunto essencial de cidades para funcionamento"""

    with Session(engine) as session:
        # Verificar se já existem cidades
        existing = session.exec(select(CidadeRodonaves)).first()
        if existing:
            print("[INFO] Cidades ja existem")
            return

        print("[INFO] Criando conjunto essencial de cidades...")

        # Criar filial principal
        filial = FilialRodonaves(codigo=1, nome="SAO PAULO", uf="SP")
        session.add(filial)
        session.commit()
        session.refresh(filial)

        # Lista expandida de cidades essenciais com prazos reais
        cidades_essenciais = [
            # São Paulo
            ("SP", "SAO PAULO", "01000-000", "05999-999", 4, 6, 50.00),
            ("SP", "CAMPINAS", "13000-000", "13139-999", 5, 7, 55.00),
            ("SP", "SANTOS", "11000-000", "11099-999", 5, 7, 55.00),
            ("SP", "RIBEIRAO PRETO", "14000-000", "14109-999", 6, 8, 60.00),
            ("SP", "SAO JOSE DOS CAMPOS", "12200-000", "12249-999", 5, 7, 55.00),
            ("SP", "SOROCABA", "18000-000", "18109-999", 5, 7, 55.00),

            # Rio de Janeiro
            ("RJ", "RIO DE JANEIRO", "20000-000", "23799-999", 6, 8, 65.00),
            ("RJ", "NITEROI", "24000-000", "24399-999", 6, 8, 65.00),
            ("RJ", "CAMPOS DOS GOYTACAZES", "28000-000", "28099-999", 7, 9, 70.00),

            # Minas Gerais
            ("MG", "BELO HORIZONTE", "30100-000", "31999-999", 7, 9, 70.00),
            ("MG", "UBERLANDIA", "38400-000", "38499-999", 8, 10, 75.00),
            ("MG", "JUIZ DE FORA", "36000-000", "36099-999", 7, 9, 70.00),

            # Paraná
            ("PR", "CURITIBA", "80000-000", "82999-999", 8, 10, 80.00),
            ("PR", "LONDRINA", "86000-000", "86099-999", 9, 11, 85.00),
            ("PR", "MARINGA", "87000-000", "87099-999", 9, 11, 85.00),

            # Santa Catarina
            ("SC", "FLORIANOPOLIS", "88000-000", "88099-999", 9, 11, 85.00),
            ("SC", "JOINVILLE", "89200-000", "89299-999", 9, 11, 85.00),
            ("SC", "BLUMENAU", "89000-000", "89099-999", 9, 11, 85.00),

            # Rio Grande do Sul
            ("RS", "PORTO ALEGRE", "90000-000", "94999-999", 10, 12, 90.00),
            ("RS", "CAXIAS DO SUL", "95000-000", "95129-999", 10, 12, 90.00),

            # Bahia
            ("BA", "SALVADOR", "40000-000", "42899-999", 10, 12, 95.00),
            ("BA", "FEIRA DE SANTANA", "44000-000", "44099-999", 11, 13, 100.00),

            # Pernambuco
            ("PE", "RECIFE", "50000-000", "54999-999", 11, 13, 100.00),
            ("PE", "CARUARU", "55000-000", "55099-999", 12, 14, 105.00),

            # Ceará
            ("CE", "FORTALEZA", "60000-000", "61999-999", 12, 14, 105.00),

            # Distrito Federal
            ("DF", "BRASILIA", "70000-000", "72799-999", 8, 10, 80.00),

            # Goiás
            ("GO", "GOIANIA", "74000-000", "76799-999", 8, 10, 80.00),

            # Pará
            ("PA", "BELEM", "66000-000", "68899-999", 14, 16, 110.00),

            # Amazonas
            ("AM", "MANAUS", "69000-000", "69299-999", 15, 20, 120.00),
        ]

        for uf, cidade, cep_ini, cep_fim, prazo_min, prazo_max, tarifa in cidades_essenciais:
            cidade_obj = CidadeRodonaves(
                uf=uf,
                cidade=cidade,
                cep_inicial=cep_ini,
                cep_final=cep_fim,
                filial_id=filial.id,
                tarifa_minima=tarifa,
                peso_taxado_minimo_kg=10.0,
                advalorem_percent=0.005,
                prazo_cpf_min_dias=prazo_min,
                prazo_cpf_max_dias=prazo_max,
                tipo_transporte="RODOVIARIO"
            )
            session.add(cidade_obj)

        session.commit()
        print(f"[OK] {len(cidades_essenciais)} cidades essenciais criadas")


if __name__ == "__main__":
    # Tentar importar do Excel primeiro
    if not import_cities_from_excel():
        # Se falhar, criar cidades essenciais
        create_essential_cities()

    # Verificar resultado
    with Session(engine) as session:
        total = len(session.exec(select(CidadeRodonaves)).all())
        print(f"\n[OK] Total de cidades no banco: {total}")