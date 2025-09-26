#!/usr/bin/env python
"""
Script para corrigir autocomplete para usar tabela Destino
"""

def create_new_autocomplete():
    return '''@router.get("/extended/autocomplete", response_class=HTMLResponse)
async def autocomplete_cidades(
    estado: str,
    q: str = Query("", alias="cidade_busca")
):
    """Autocomplete para busca de cidades usando tabela Destino"""

    if len(q) < 2:
        return ""

    logger.info(f"[AUTOCOMPLETE] Busca por '{q}' no estado '{estado}'")

    with Session(engine) as session:
        try:
            # Normalizar estado para uppercase e validar
            estado_normalizado = estado.strip().upper()
            logger.info(f"[AUTOCOMPLETE] Estado normalizado: '{estado_normalizado}'")

            # Verificar se estado existe
            estado_obj = session.exec(
                select(Estado).where(Estado.sigla.ilike(estado_normalizado))
            ).first()

            if not estado_obj:
                logger.error(f"[AUTOCOMPLETE] Estado não encontrado: '{estado}'")
                # Listar estados disponíveis
                estados_disponiveis = session.exec(select(Estado)).all()
                estados_list = [e.sigla for e in estados_disponiveis]
                return div({"class": "error"},
                    f"Estado '{estado}' não encontrado. Estados disponíveis: {', '.join(estados_list)}")

            # Normalizar termo de busca
            termo_normalizado = normalizar_texto(q)
            logger.info(f"[AUTOCOMPLETE] Termo normalizado: '{termo_normalizado}'")

            # Buscar cidades na tabela Destino
            logger.info("[AUTOCOMPLETE] Buscando cidades na tabela Destino...")

            # Estratégia 1: Busca exata por nome normalizado
            cidades_exatas = session.exec(
                select(Destino).where(
                    and_(
                        Destino.uf == estado_normalizado,
                        Destino.cidade.ilike(q)
                    )
                ).limit(5)
            ).all()

            logger.info(f"[AUTOCOMPLETE] Estratégia 1 - Encontradas {len(cidades_exatas)} cidades exatas")

            # Estratégia 2: Busca por início
            if len(cidades_exatas) < 5:
                cidades_inicio = session.exec(
                    select(Destino).where(
                        and_(
                            Destino.uf == estado_normalizado,
                            Destino.cidade.ilike(f"{q}%")
                        )
                    ).limit(10)
                ).all()
                logger.info(f"[AUTOCOMPLETE] Estratégia 2 - Encontradas {len(cidades_inicio)} cidades por início")
            else:
                cidades_inicio = []

            # Estratégia 3: Busca por conteúdo
            if len(cidades_exatas) + len(cidades_inicio) < 5:
                cidades_conteudo = session.exec(
                    select(Destino).where(
                        and_(
                            Destino.uf == estado_normalizado,
                            Destino.cidade.ilike(f"%{q}%")
                        )
                    ).limit(10)
                ).all()
                logger.info(f"[AUTOCOMPLETE] Estratégia 3 - Encontradas {len(cidades_conteudo)} cidades por conteúdo")
            else:
                cidades_conteudo = []

            # Combinar resultados removendo duplicatas
            cidades_encontradas = []
            ids_vistos = set()

            for cidade in cidades_exatas + cidades_inicio + cidades_conteudo:
                if cidade.id not in ids_vistos:
                    cidades_encontradas.append(cidade)
                    ids_vistos.add(cidade.id)

            logger.info(f"[AUTOCOMPLETE] Total de cidades únicas encontradas: {len(cidades_encontradas)}")

            if not cidades_encontradas:
                # Mostrar amostra de cidades disponíveis neste estado
                amostra = session.exec(
                    select(Destino).where(Destino.uf == estado_normalizado).limit(5)
                ).all()

                if amostra:
                    cidades_exemplo = [c.cidade for c in amostra]
                    return div({"class": "info"},
                        f"Nenhuma cidade encontrada para '{q}'. Exemplos em {estado_normalizado}: {', '.join(cidades_exemplo)}")
                else:
                    return div({"class": "info"}, f"Nenhuma cidade encontrada para '{q}' em {estado_normalizado}")

            # Gerar sugestões HTML
            items = []
            for cidade in cidades_encontradas[:10]:  # Limitar a 10 resultados
                try:
                    # Escapar aspas simples para JavaScript
                    cidade_nome_escaped = cidade.cidade.replace("'", "\\\\'")

                    onclick = f"document.getElementById('cidade_busca').value='{cidade_nome_escaped}'; "
                    onclick += f"document.getElementById('cidade_id').value='{cidade.id}'; "
                    onclick += "document.getElementById('cidade-suggestions').innerHTML='';"

                    # Informações da cidade
                    categoria_info = ""
                    if hasattr(cidade, 'categoria') and cidade.categoria:
                        categoria_info = f" ({cidade.categoria})"

                    items.append(
                        div(
                            {"onclick": onclick, "class": "suggestion-item"},
                            strong({}, cidade.cidade),
                            span({"class": "categoria"}, categoria_info)
                        )
                    )

                    logger.info(f"[AUTOCOMPLETE] Adicionada sugestão: {cidade.cidade}")

                except Exception as e:
                    logger.error(f"[AUTOCOMPLETE] Erro ao processar cidade {cidade.cidade}: {e}")
                    continue

            logger.info(f"[AUTOCOMPLETE] Retornando {len(items)} sugestões")
            return div({"class": "suggestions"}, *items)

        except Exception as e:
            logger.error(f"[AUTOCOMPLETE] Erro inesperado: {e}")
            import traceback
            logger.error(f"[AUTOCOMPLETE] Stack trace: {traceback.format_exc()}")
            return div({"class": "error"}, "Erro interno na busca de cidades")'''

if __name__ == "__main__":
    print("Nova função de autocomplete criada!")
    print(create_new_autocomplete())