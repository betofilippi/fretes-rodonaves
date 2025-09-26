"""
VIEWS CORRIGIDAS PARA USAR TABELA DESTINO
"""

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse
from sqlmodel import Session, select, and_

from .db import engine
from .models import Destino
from .models_extended import Estado
from .fasthtml import *

router = APIRouter()

@router.get("/extended/autocomplete", response_class=HTMLResponse)
async def autocomplete_cidades(
    estado: str,
    q: str = Query("", alias="cidade_busca")
):
    """Autocomplete SIMPLES e FUNCIONAL para tabela Destino"""

    if len(q) < 2:
        return ""

    with Session(engine) as session:
        try:
            # Normalizar estado
            estado_normalizado = estado.strip().upper()

            # Buscar cidades na tabela Destino (onde estão as 4044 cidades!)
            cidades = session.exec(
                select(Destino).where(
                    and_(
                        Destino.uf == estado_normalizado,
                        Destino.cidade.ilike(f"{q}%")
                    )
                ).limit(10)
            ).all()

            # Se não encontrou, busca mais flexível
            if not cidades:
                cidades = session.exec(
                    select(Destino).where(
                        and_(
                            Destino.uf == estado_normalizado,
                            Destino.cidade.ilike(f"%{q}%")
                        )
                    ).limit(10)
                ).all()

            if not cidades:
                return div({}, "Nenhuma cidade encontrada")

            # Gerar sugestões HTML
            items = []
            for cidade in cidades:
                # JavaScript onclick
                onclick = f"document.getElementById('cidade_busca').value='{cidade.cidade}'; "
                onclick += f"document.getElementById('cidade_id').value='{cidade.id}'; "
                onclick += "document.getElementById('cidade-suggestions').innerHTML='';"

                items.append(
                    div({"onclick": onclick, "style": "cursor: pointer; padding: 5px; border-bottom: 1px solid #eee;"},
                        strong({}, cidade.cidade),
                        span({"style": "color: #666; margin-left: 10px;"}, f"({cidade.categoria})")
                    )
                )

            return div({"style": "background: white; border: 1px solid #ccc; max-height: 200px; overflow-y: auto;"}, *items)

        except Exception as e:
            return div({}, f"Erro: {str(e)}")


# Teste da função
def test_autocomplete():
    """Testar autocomplete localmente"""
    print("Testando autocomplete...")

    with Session(engine) as session:
        # Contar destinos
        total_destinos = len(session.exec(select(Destino)).all())
        print(f"Total de destinos: {total_destinos}")

        # Testar busca por SP
        sp_cidades = session.exec(
            select(Destino).where(Destino.uf == "SP").limit(5)
        ).all()

        print(f"Primeiras 5 cidades de SP:")
        for cidade in sp_cidades:
            print(f"  - {cidade.cidade} ({cidade.categoria})")

        # Testar busca específica
        sao_paulo = session.exec(
            select(Destino).where(
                and_(Destino.uf == "SP", Destino.cidade.ilike("SAO%"))
            )
        ).all()

        print(f"Cidades que começam com 'SAO' em SP: {len(sao_paulo)}")
        for cidade in sao_paulo[:3]:
            print(f"  - {cidade.cidade}")

if __name__ == "__main__":
    test_autocomplete()