#!/usr/bin/env python
"""
Script de importação de cidades CORRIGIDO
Usa o modelo Destino que está funcionando
"""

import os
import sys
import pandas as pd
from pathlib import Path

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent))

from frete_app.db import engine, create_db_and_tables
from sqlmodel import Session, select
from frete_app.models import Destino

def import_cities_simple():
    """Importa cidades usando o modelo Destino simples"""
    print("=== IMPORTAÇÃO DE CIDADES - MODELO SIMPLES ===")

    # Criar tabelas se não existirem
    create_db_and_tables()

    with Session(engine) as session:
        # Limpar destinos existentes
        existing = session.exec(select(Destino)).all()
        if existing:
            print(f"Removendo {len(existing)} destinos existentes...")
            for destino in existing:
                session.delete(destino)
            session.commit()

        cities_imported = 0

        # Importar do arquivo de cidades
        cities_file = "Relação Cidades Atendidas Modal Rodoviário_25_03_25.xlsx"
        if os.path.exists(cities_file):
            print(f"Importando de {cities_file}...")
            try:
                df = pd.read_excel(cities_file, sheet_name=0)
                print(f"Arquivo carregado: {len(df)} linhas")

                # Mapear cidades únicas
                cidade_set = set()

                for idx, row in df.iterrows():
                    if idx < 3:  # Skip headers
                        continue

                    try:
                        # Extrair dados baseado na estrutura conhecida
                        # Coluna 7: Cidade destino, Coluna 8: UF destino
                        cidade_nome = str(row.iloc[7]).strip().upper() if pd.notna(row.iloc[7]) else ""
                        uf = str(row.iloc[8]).strip()[:2].upper() if pd.notna(row.iloc[8]) else ""

                        if not cidade_nome or not uf or len(uf) != 2:
                            continue

                        # Determinar categoria
                        categoria = "INTERIOR_1"
                        # Capitais e grandes centros
                        if "CAPITAL" in cidade_nome or cidade_nome in [
                            "SÃO PAULO", "RIO DE JANEIRO", "BELO HORIZONTE", "SALVADOR",
                            "BRASÍLIA", "FORTALEZA", "RECIFE", "CURITIBA", "PORTO ALEGRE",
                            "MANAUS", "BELÉM", "GOIÂNIA", "CAMPINAS", "SÃO BERNARDO DO CAMPO",
                            "SANTOS", "OSASCO", "SANTO ANDRÉ", "SÃO JOSÉ DOS CAMPOS"
                        ]:
                            categoria = "CAPITAL"

                        # Chave única
                        key = f"{uf}_{cidade_nome}"
                        if key not in cidade_set:
                            cidade_set.add(key)

                            destino = Destino(
                                uf=uf,
                                cidade=cidade_nome,
                                categoria=categoria
                            )
                            session.add(destino)
                            cities_imported += 1

                            if cities_imported % 200 == 0:
                                session.commit()
                                print(f"  {cities_imported} cidades importadas...")

                    except Exception as e:
                        print(f"  Erro linha {idx}: {e}")
                        continue

                # Commit final
                session.commit()
                print(f"[OK] {cities_imported} cidades importadas do arquivo principal")

                # Verificar total
                total_cities = len(session.exec(select(Destino)).all())
                print(f"[OK] Total de cidades no banco: {total_cities}")

                return total_cities

            except Exception as e:
                print(f"[ERRO] Falha ao importar cidades: {e}")
                return 0
        else:
            print(f"[ERRO] Arquivo {cities_file} não encontrado")
            return 0

def create_sample_data():
    """Cria dados de exemplo para teste"""
    print("\n=== CRIANDO DADOS DE EXEMPLO ===")

    from frete_app.models import VersaoTabela, ParametrosGerais, TarifaPeso

    with Session(engine) as session:
        # Verificar se já tem dados
        versao = session.exec(select(VersaoTabela).where(VersaoTabela.ativa == True)).first()
        if versao:
            print("Versão de tabela já existe")
            return True

        # Criar versão da tabela
        versao = VersaoTabela(
            nome="Tabela Teste 2025",
            descricao="Tabela de teste para validação",
            ativa=True
        )
        session.add(versao)
        session.commit()
        session.refresh(versao)
        print(f"Versão criada: {versao.nome}")

        # Criar parâmetros gerais
        parametros = ParametrosGerais(
            versao_id=versao.id,
            cubagem_kg_por_m3=300.0,
            fvalor_percent_padrao=0.005,
            fvalor_min=4.78,
            gris_percent_ate_10k=0.001,
            gris_percent_acima_10k=0.0023,
            gris_min=1.10,
            pedagio_por_100kg=3.80,
            icms_percent=0.12
        )
        session.add(parametros)
        print("Parâmetros gerais criados")

        # Criar tarifas por categoria
        categorias = ["CAPITAL", "INTERIOR_1", "INTERIOR_2"]
        for categoria in categorias:
            tarifa = TarifaPeso(
                versao_id=versao.id,
                categoria=categoria,
                ate_10=35.00 if categoria == "CAPITAL" else 40.00,
                ate_20=42.00 if categoria == "CAPITAL" else 48.00,
                ate_40=58.00 if categoria == "CAPITAL" else 65.00,
                ate_60=75.00 if categoria == "CAPITAL" else 82.00,
                ate_100=98.00 if categoria == "CAPITAL" else 105.00,
                excedente_por_kg=1.20 if categoria == "CAPITAL" else 1.35
            )
            session.add(tarifa)
            print(f"Tarifa criada para {categoria}")

        session.commit()
        print("[OK] Dados de exemplo criados")
        return True

def run_complete_import():
    """Executa importação completa"""
    print("=" * 60)
    print("IMPORTAÇÃO COMPLETA DE CIDADES - MODELO CORRIGIDO")
    print("=" * 60)

    try:
        # 1. Importar cidades
        total_cities = import_cities_simple()

        if total_cities < 100:
            print(f"[AVISO] Apenas {total_cities} cidades importadas")
            print("Isso pode indicar problema na estrutura do Excel")

        # 2. Criar dados de exemplo
        create_sample_data()

        # 3. Verificação final
        with Session(engine) as session:
            cidades_count = len(session.exec(select(Destino)).all())
            versoes_count = len(session.exec(select(VersaoTabela)).all())

            print("\n" + "=" * 60)
            print("RELATÓRIO FINAL")
            print("=" * 60)
            print(f"Total de cidades: {cidades_count}")
            print(f"Versões de tabela: {versoes_count}")

            if cidades_count > 0 and versoes_count > 0:
                print("[SUCCESS] Sistema pronto para testes!")
                return True
            else:
                print("[ERROR] Dados insuficientes")
                return False

    except Exception as e:
        print(f"[ERROR] Erro na importação: {e}")
        return False

if __name__ == "__main__":
    success = run_complete_import()
    sys.exit(0 if success else 1)