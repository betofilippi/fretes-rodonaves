#!/usr/bin/env python
"""
Script para inicializar o banco de dados com todos os dados necessários
"""

import os
import sys
import time
from pathlib import Path

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent))

def init_database():
    """Inicializa o banco de dados com todos os dados necessários"""

    print("[INFO] Iniciando configuracao do banco de dados...")

    # Importar após adicionar ao path
    from frete_app.db import create_db_and_tables, engine
    from frete_app.seed_data import seed_initial_data
    from sqlmodel import Session, select

    # Criar tabelas
    print("[INFO] Criando tabelas do banco de dados...")
    create_db_and_tables()
    print("[OK] Tabelas criadas com sucesso")

    # Popular dados iniciais (produtos, destinos, etc)
    print("[INFO] Populando dados iniciais...")
    seed_initial_data()
    print("[OK] Dados iniciais populados")

    # Importar dados estendidos
    try:
        print("[INFO] Importando dados de cidades e tarifas...")

        # Verificar se já tem dados de cidades
        from frete_app.models_extended import CidadeRodonaves
        with Session(engine) as session:
            cidade_count = session.exec(select(CidadeRodonaves)).first()

            if not cidade_count:
                print("[INFO] Importando cidades do Brasil...")
                # Importar TDA e TRT
                from import_tda import import_tda_data
                from import_trt import import_trt_data

                import_tda_data()
                print("[OK] TDA importado")

                import_trt_data()
                print("[OK] TRT importado")

                # Importar prazos de entrega
                try:
                    from import_delivery_times import import_delivery_times
                    import_delivery_times()
                    print("[OK] Prazos de entrega importados")
                except Exception as e:
                    print(f"[AVISO] Nao foi possivel importar prazos: {e}")
            else:
                print("[INFO] Dados de cidades ja existem, pulando importacao")

    except Exception as e:
        print(f"[ERRO] Erro ao importar dados estendidos: {e}")
        print("[INFO] Continuando sem dados estendidos...")

    # Verificar integridade
    print("[INFO] Verificando integridade do banco...")

    from frete_app.models import Produto, Destino, VersaoTabela, TarifaPeso
    from frete_app.models_extended import Estado, FilialRodonaves

    with Session(engine) as session:
        # Contar registros
        produtos = len(session.exec(select(Produto)).all())
        destinos = len(session.exec(select(Destino)).all())
        versoes = len(session.exec(select(VersaoTabela)).all())
        tarifas = len(session.exec(select(TarifaPeso)).all())

        print(f"[OK] Produtos: {produtos}")
        print(f"[OK] Destinos: {destinos}")
        print(f"[OK] Versoes: {versoes}")
        print(f"[OK] Tarifas: {tarifas}")

        # Verificar dados estendidos
        try:
            estados = len(session.exec(select(Estado)).all())
            filiais = len(session.exec(select(FilialRodonaves)).all())
            cidades = len(session.exec(select(CidadeRodonaves)).all())

            print(f"[OK] Estados: {estados}")
            print(f"[OK] Filiais: {filiais}")
            print(f"[OK] Cidades: {cidades}")
        except:
            print("[INFO] Dados estendidos nao disponiveis")

    print("[OK] Banco de dados inicializado com sucesso!")
    return True

if __name__ == "__main__":
    try:
        # Aguardar um momento para garantir que o serviço está pronto
        time.sleep(2)

        if init_database():
            print("\n[OK] Inicializacao concluida com sucesso!")
            sys.exit(0)
        else:
            print("\n[ERRO] Falha na inicializacao")
            sys.exit(1)
    except Exception as e:
        print(f"\n[ERRO] Erro fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)