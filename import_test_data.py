#!/usr/bin/env python3
"""
Import Test Data - Products and Cities
Creates minimal test data for calculation testing
"""

import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from sqlmodel import Session
from frete_app.db import engine, create_db_and_tables
from frete_app.models import Produto
from frete_app.models_extended import Estado, CidadeRodonaves


def import_test_data():
    """Import essential test data"""

    print("Importing test data...")

    with Session(engine) as session:
        # Create states
        estados = [
            Estado(id=1, sigla="SC", nome="Santa Catarina", regiao="Sul", tem_cobertura=True),
            Estado(id=2, sigla="SP", nome="São Paulo", regiao="Sudeste", tem_cobertura=True)
        ]

        for estado in estados:
            existing = session.get(Estado, estado.id)
            if not existing:
                session.add(estado)
                print(f"Added state: {estado.sigla}")

        session.commit()

        # Create products with correct Juna specifications
        produtos = [
            Produto(
                id=1,
                nome="Zilla",
                largura_cm=111.0,
                altura_cm=111.0,
                profundidade_cm=150.0,
                peso_real_kg=63.0,
                valor_nf_padrao=8100.0
            ),
            Produto(
                id=2,
                nome="Juna",
                largura_cm=78.0,  # Correct dimensions from specification
                altura_cm=186.0,
                profundidade_cm=128.0,
                peso_real_kg=123.0,  # Correct weight
                valor_nf_padrao=15000.0
            )
        ]

        for produto in produtos:
            existing = session.get(Produto, produto.id)
            if not existing:
                session.add(produto)
                print(f"Added product: {produto.nome} ({produto.largura_cm}x{produto.altura_cm}x{produto.profundidade_cm}cm, {produto.peso_real_kg}kg)")

        session.commit()

        # Create test cities
        cidades = [
            CidadeRodonaves(
                id=1,
                nome="BALNEARIO CAMBORIU",
                estado_id=1,  # SC
                filial_atendimento_id=1,
                categoria_tarifa="INTERIOR_2",
                distancia_km=50.0,
                prazo_entrega_dias=1,
                tem_restricao_entrega=False,
                tem_tda=False,
                tem_trt=False,
                ativo=True
            ),
            CidadeRodonaves(
                id=2,
                nome="SAO PAULO",
                estado_id=2,  # SP
                filial_atendimento_id=2,
                categoria_tarifa="CAPITAL",
                distancia_km=300.0,
                prazo_entrega_dias=2,
                tem_restricao_entrega=False,
                tem_tda=False,
                tem_trt=False,
                ativo=True
            )
        ]

        for cidade in cidades:
            existing = session.get(CidadeRodonaves, cidade.id)
            if not existing:
                session.add(cidade)
                print(f"Added city: {cidade.nome}/{estados[cidade.estado_id-1].sigla} ({cidade.categoria_tarifa})")

        session.commit()
        print("Test data imported successfully!")


def main():
    """Main execution"""
    try:
        create_db_and_tables()
        import_test_data()
        return 0
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())