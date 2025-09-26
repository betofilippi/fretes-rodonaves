#!/usr/bin/env python
"""
Script robusto para inicializar o banco de dados em produção
Garante que todos os dados sejam carregados mesmo se alguns arquivos falharem
"""

import os
import sys
from pathlib import Path

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent))

def init_production_database():
    """Inicializa o banco de dados com verificações robustas"""

    print("[INFO] Iniciando configuracao do banco de dados para producao...")

    # Importar após adicionar ao path
    from frete_app.db import create_db_and_tables, engine
    from sqlmodel import Session, select

    # Criar tabelas
    print("[INFO] Criando tabelas do banco de dados...")
    try:
        create_db_and_tables()
        print("[OK] Tabelas criadas")
    except Exception as e:
        print(f"[ERRO] Falha ao criar tabelas: {e}")
        return False

    # 1. PRODUTOS - Dados essenciais hardcoded
    print("[INFO] Verificando produtos...")
    from frete_app.models import Produto

    with Session(engine) as session:
        existing = session.exec(select(Produto)).first()
        if not existing:
            print("[INFO] Criando produtos...")
            produtos = [
                Produto(nome="Juna", largura_cm=78.0, altura_cm=186.0,
                       profundidade_cm=128.0, peso_real_kg=123.0, valor_nf_padrao=2500.00),
                Produto(nome="Kimbo", largura_cm=78.0, altura_cm=186.0,
                       profundidade_cm=128.0, peso_real_kg=121.0, valor_nf_padrao=2500.00),
                Produto(nome="Kay", largura_cm=78.0, altura_cm=186.0,
                       profundidade_cm=128.0, peso_real_kg=161.0, valor_nf_padrao=3000.00),
                Produto(nome="Jaya", largura_cm=78.0, altura_cm=186.0,
                       profundidade_cm=128.0, peso_real_kg=107.0, valor_nf_padrao=2200.00),
            ]
            for p in produtos:
                session.add(p)
            session.commit()
            print(f"[OK] {len(produtos)} produtos criados")
        else:
            print("[OK] Produtos ja existem")

    # 2. ESTADOS - Dados essenciais hardcoded
    print("[INFO] Verificando estados...")
    from frete_app.models_extended import Estado

    with Session(engine) as session:
        existing = session.exec(select(Estado)).first()
        if not existing:
            print("[INFO] Criando estados...")
            estados_brasil = [
                ("AC", "Acre"), ("AL", "Alagoas"), ("AP", "Amapá"), ("AM", "Amazonas"),
                ("BA", "Bahia"), ("CE", "Ceará"), ("DF", "Distrito Federal"),
                ("ES", "Espírito Santo"), ("GO", "Goiás"), ("MA", "Maranhão"),
                ("MT", "Mato Grosso"), ("MS", "Mato Grosso do Sul"),
                ("MG", "Minas Gerais"), ("PA", "Pará"), ("PB", "Paraíba"),
                ("PR", "Paraná"), ("PE", "Pernambuco"), ("PI", "Piauí"),
                ("RJ", "Rio de Janeiro"), ("RN", "Rio Grande do Norte"),
                ("RS", "Rio Grande do Sul"), ("RO", "Rondônia"), ("RR", "Roraima"),
                ("SC", "Santa Catarina"), ("SP", "São Paulo"), ("SE", "Sergipe"),
                ("TO", "Tocantins")
            ]
            for uf, nome in estados_brasil:
                session.add(Estado(sigla=uf, nome=nome))
            session.commit()
            print(f"[OK] {len(estados_brasil)} estados criados")
        else:
            print("[OK] Estados ja existem")

    # 3. FILIAIS E CIDADES - Tentar importar dos Excel ou usar fallback
    print("[INFO] Verificando cidades...")
    from frete_app.models_extended import CidadeRodonaves, FilialRodonaves

    with Session(engine) as session:
        cidade_count = session.exec(select(CidadeRodonaves)).first()

        if not cidade_count:
            print("[INFO] Importando cidades...")

            # Usar o novo script de importação que tem fallback embutido
            try:
                from import_cities_data import import_cities_from_excel, create_essential_cities

                # Tentar importar do Excel
                if not import_cities_from_excel():
                    # Se falhar, criar cidades essenciais
                    create_essential_cities()
                    print("[OK] Cidades essenciais criadas")
                else:
                    print("[OK] Cidades importadas do Excel")

            except Exception as e:
                print(f"[ERRO] Falha na importacao de cidades: {e}")
                # Fallback final - criar cidades mínimas
                try:
                    criar_cidades_minimas(session)
                    print("[OK] Cidades minimas criadas como fallback")
                except Exception as e2:
                    print(f"[ERRO] Falha total ao criar cidades: {e2}")
        else:
            print("[OK] Cidades ja existem")

    # 4. Verificação final
    print("\n[INFO] Verificacao final do banco...")
    with Session(engine) as session:
        from frete_app.models import Produto, VersaoTabela, ParametrosGerais
        from frete_app.models_extended import Estado, FilialRodonaves, CidadeRodonaves

        produtos = len(session.exec(select(Produto)).all())
        estados = len(session.exec(select(Estado)).all())
        filiais = len(session.exec(select(FilialRodonaves)).all())
        cidades = len(session.exec(select(CidadeRodonaves)).all())

        print(f"[OK] Produtos: {produtos}")
        print(f"[OK] Estados: {estados}")
        print(f"[OK] Filiais: {filiais}")
        print(f"[OK] Cidades: {cidades}")

        if produtos > 0 and estados > 0:
            print("\n[OK] Banco inicializado com sucesso!")
            return True
        else:
            print("\n[ERRO] Banco nao foi inicializado corretamente")
            return False

def criar_cidades_minimas(session):
    """Cria conjunto mínimo de cidades para funcionamento básico"""
    from frete_app.models_extended import FilialRodonaves, CidadeRodonaves

    print("[INFO] Criando conjunto minimo de cidades...")

    # Criar filial padrão
    filial = FilialRodonaves(
        codigo=1,
        nome="SAO PAULO",
        uf="SP"
    )
    session.add(filial)
    session.commit()
    session.refresh(filial)

    # Criar cidades principais
    cidades_principais = [
        ("SP", "SAO PAULO", "01310-100", 4, 6),
        ("SP", "CAMPINAS", "13015-000", 5, 7),
        ("RJ", "RIO DE JANEIRO", "20040-020", 6, 8),
        ("MG", "BELO HORIZONTE", "30190-000", 7, 9),
        ("PR", "CURITIBA", "80010-000", 8, 10),
        ("RS", "PORTO ALEGRE", "90010-000", 9, 11),
        ("BA", "SALVADOR", "40015-000", 10, 12),
        ("PE", "RECIFE", "50030-000", 11, 13),
        ("CE", "FORTALEZA", "60025-000", 12, 14),
        ("DF", "BRASILIA", "70040-020", 8, 10),
    ]

    for uf, cidade, cep, prazo_min, prazo_max in cidades_principais:
        cidade_obj = CidadeRodonaves(
            uf=uf,
            cidade=cidade,
            cep_inicial=cep[:5] + "-000",
            cep_final=cep[:5] + "-999",
            filial_id=filial.id,
            tarifa_minima=50.00,
            peso_taxado_minimo_kg=10.0,
            advalorem_percent=0.005,
            prazo_cpf_min_dias=prazo_min,
            prazo_cpf_max_dias=prazo_max,
            tipo_transporte="RODOVIARIO"
        )
        session.add(cidade_obj)

    session.commit()
    print(f"[OK] {len(cidades_principais)} cidades principais criadas")

if __name__ == "__main__":
    try:
        import time
        time.sleep(1)  # Pequena pausa para garantir que serviços estejam prontos

        if init_production_database():
            print("\n[OK] Inicializacao concluida!")
            sys.exit(0)
        else:
            print("\n[ERRO] Inicializacao falhou")
            sys.exit(1)
    except Exception as e:
        print(f"\n[ERRO] Erro fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)