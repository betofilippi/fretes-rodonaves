#!/usr/bin/env python
"""
Script para verificar cidades no banco de dados
"""

import sys
from pathlib import Path

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent))

from frete_app.db import engine
from sqlmodel import Session, select
from frete_app.models import Destino

def verify_cities():
    """Verifica as cidades no banco"""
    print("=== VERIFICAÇÃO DE CIDADES NO BANCO ===")

    with Session(engine) as session:
        # Contar total
        all_cities = session.exec(select(Destino)).all()
        print(f"Total de cidades: {len(all_cities)}")

        # Contar por UF
        ufs = {}
        for city in all_cities:
            if city.uf in ufs:
                ufs[city.uf] += 1
            else:
                ufs[city.uf] = 1

        print(f"\nCidades por UF (primeiras 20):")
        count = 0
        for uf, qty in sorted(ufs.items()):
            if count < 20:
                print(f"  {uf}: {qty} cidades")
                count += 1

        # Buscar exemplos de cidades conhecidas
        print(f"\nExemplos de busca:")
        test_cities = ["SAO PAULO", "RIO DE JANEIRO", "CURITIBA", "PORTO ALEGRE"]

        for test_city in test_cities:
            results = session.exec(
                select(Destino).where(
                    Destino.cidade.ilike(f"%{test_city}%")
                )
            ).all()
            print(f"  '{test_city}': {len(results)} resultados")
            if results:
                for result in results[:3]:  # Mostrar apenas 3 primeiros
                    print(f"    - {result.cidade} ({result.uf}) - {result.categoria}")

        # Verificar categorias
        categorias = {}
        for city in all_cities:
            if city.categoria in categorias:
                categorias[city.categoria] += 1
            else:
                categorias[city.categoria] = 1

        print(f"\nCidades por categoria:")
        for cat, qty in categorias.items():
            print(f"  {cat}: {qty} cidades")

        return len(all_cities)

if __name__ == "__main__":
    total = verify_cities()
    print(f"\n[RESULTADO] {total} cidades encontradas no banco")