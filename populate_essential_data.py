#!/usr/bin/env python
"""
Script simples para popular dados essenciais no banco
"""

import sys
from pathlib import Path

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent))

from frete_app.db import create_db_and_tables, engine
from frete_app.models_extended import Estado, FilialRodonaves, CidadeRodonaves
from sqlmodel import Session, select

def populate_essential_data():
    """Popula dados essenciais para o funcionamento do sistema"""

    print("[INFO] Criando dados essenciais...")

    # Criar tabelas
    create_db_and_tables()

    with Session(engine) as session:
        # 1. Verificar e criar estados
        existing_states = session.exec(select(Estado)).first()
        if not existing_states:
            print("[INFO] Criando estados...")
            estados_brasil = [
                ("AC", "Acre", "Norte"), ("AL", "Alagoas", "Nordeste"), ("AP", "Amapá", "Norte"),
                ("AM", "Amazonas", "Norte"), ("BA", "Bahia", "Nordeste"), ("CE", "Ceará", "Nordeste"),
                ("DF", "Distrito Federal", "Centro-Oeste"), ("ES", "Espírito Santo", "Sudeste"),
                ("GO", "Goiás", "Centro-Oeste"), ("MA", "Maranhão", "Nordeste"), ("MT", "Mato Grosso", "Centro-Oeste"),
                ("MS", "Mato Grosso do Sul", "Centro-Oeste"), ("MG", "Minas Gerais", "Sudeste"),
                ("PA", "Pará", "Norte"), ("PB", "Paraíba", "Nordeste"), ("PR", "Paraná", "Sul"),
                ("PE", "Pernambuco", "Nordeste"), ("PI", "Piauí", "Nordeste"), ("RJ", "Rio de Janeiro", "Sudeste"),
                ("RN", "Rio Grande do Norte", "Nordeste"), ("RS", "Rio Grande do Sul", "Sul"),
                ("RO", "Rondônia", "Norte"), ("RR", "Roraima", "Norte"), ("SC", "Santa Catarina", "Sul"),
                ("SP", "São Paulo", "Sudeste"), ("SE", "Sergipe", "Nordeste"), ("TO", "Tocantins", "Norte")
            ]

            for uf, nome, regiao in estados_brasil:
                estado = Estado(sigla=uf, nome=nome, regiao=regiao, tem_cobertura=True)
                session.add(estado)

            session.commit()
            print(f"[OK] {len(estados_brasil)} estados criados")

        # 2. Buscar estados para usar nas filiais e cidades
        estados = {estado.sigla: estado for estado in session.exec(select(Estado)).all()}

        # 3. Verificar e criar filiais
        existing_filials = session.exec(select(FilialRodonaves)).first()
        if not existing_filials:
            print("[INFO] Criando filiais...")
            filiais = [
                ("SPO", "SAO PAULO", "SAO PAULO", "SP", "MATRIZ"),
                ("RJO", "RIO DE JANEIRO", "RIO DE JANEIRO", "RJ", "FILIAL"),
                ("BHO", "BELO HORIZONTE", "BELO HORIZONTE", "MG", "FILIAL"),
                ("CWB", "CURITIBA", "CURITIBA", "PR", "FILIAL"),
                ("POA", "PORTO ALEGRE", "PORTO ALEGRE", "RS", "FILIAL"),
            ]

            for codigo, nome, cidade, uf, tipo in filiais:
                estado = estados.get(uf)
                if estado:
                    filial = FilialRodonaves(
                        codigo=codigo,
                        nome=nome,
                        cidade=cidade,
                        estado_id=estado.id,
                        tipo=tipo,
                        ativa=True
                    )
                    session.add(filial)

            session.commit()
            print(f"[OK] {len(filiais)} filiais criadas")

        # 4. Verificar e criar cidades
        existing_cities = session.exec(select(CidadeRodonaves)).first()
        if not existing_cities:
            print("[INFO] Criando cidades...")

            # Buscar filiais para usar nas cidades
            filiais = {filial.codigo: filial for filial in session.exec(select(FilialRodonaves)).all()}

            cidades = [
                ("SP", "SAO PAULO", "SPO", "CAPITAL", 4, 6),
                ("SP", "CAMPINAS", "SPO", "INTERIOR_1", 5, 7),
                ("SP", "SANTOS", "SPO", "INTERIOR_1", 5, 7),
                ("RJ", "RIO DE JANEIRO", "RJO", "CAPITAL", 6, 8),
                ("RJ", "NITEROI", "RJO", "INTERIOR_1", 6, 8),
                ("MG", "BELO HORIZONTE", "BHO", "CAPITAL", 7, 9),
                ("MG", "CONTAGEM", "BHO", "INTERIOR_1", 7, 9),
                ("PR", "CURITIBA", "CWB", "CAPITAL", 8, 10),
                ("PR", "LONDRINA", "CWB", "INTERIOR_1", 8, 10),
                ("RS", "PORTO ALEGRE", "POA", "CAPITAL", 9, 11),
                ("RS", "CAXIAS DO SUL", "POA", "INTERIOR_1", 9, 11),
                ("ES", "VITORIA", "SPO", "CAPITAL", 6, 8),
                ("ES", "VILA VELHA", "SPO", "INTERIOR_1", 6, 8),
                ("GO", "GOIANIA", "SPO", "CAPITAL", 8, 10),
                ("GO", "APARECIDA DE GOIANIA", "SPO", "INTERIOR_1", 8, 10),
                ("DF", "BRASILIA", "SPO", "CAPITAL", 8, 10),
                ("MS", "CAMPO GRANDE", "SPO", "CAPITAL", 10, 12),
                ("MT", "CUIABA", "SPO", "CAPITAL", 12, 14),
                ("SC", "FLORIANOPOLIS", "POA", "CAPITAL", 8, 10),
                ("SC", "JOINVILLE", "POA", "INTERIOR_1", 8, 10),
            ]

            for uf, nome_cidade, codigo_filial, categoria, prazo_min, prazo_max in cidades:
                estado = estados.get(uf)
                filial = filiais.get(codigo_filial)

                if estado and filial:
                    cidade = CidadeRodonaves(
                        nome=nome_cidade,
                        estado_id=estado.id,
                        filial_atendimento_id=filial.id,
                        categoria_tarifa=categoria,
                        prazo_cpf_min_dias=prazo_min,
                        prazo_cpf_max_dias=prazo_max,
                        tipo_transporte="RODOVIARIO",
                        tem_tda=False,
                        tem_trt=False,
                        ativo=True
                    )
                    session.add(cidade)

            session.commit()
            print(f"[OK] {len(cidades)} cidades criadas")

        # 5. Verificação final
        print("\n[INFO] Verificacao final...")
        total_estados = len(session.exec(select(Estado)).all())
        total_filiais = len(session.exec(select(FilialRodonaves)).all())
        total_cidades = len(session.exec(select(CidadeRodonaves)).all())

        print(f"[OK] Estados: {total_estados}")
        print(f"[OK] Filiais: {total_filiais}")
        print(f"[OK] Cidades: {total_cidades}")

        return total_estados > 0 and total_filiais > 0 and total_cidades > 0

if __name__ == "__main__":
    try:
        if populate_essential_data():
            print("\n[OK] Dados essenciais criados com sucesso!")
            sys.exit(0)
        else:
            print("\n[ERRO] Falha ao criar dados essenciais")
            sys.exit(1)
    except Exception as e:
        print(f"\n[ERRO] Erro: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)