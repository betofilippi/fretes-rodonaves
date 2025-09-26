"""
Views estendidas com suporte a busca de cidades e taxas especiais
"""

import logging
import re
import unicodedata
from fastapi import APIRouter, Request, Form, Query, HTTPException
from fastapi.responses import HTMLResponse
from typing import Optional, List
from sqlmodel import Session, select, or_, and_

from .db import engine
from .models import Produto, VersaoTabela
from .models import Destino
from .models_extended import CidadeRodonaves, Estado, TaxaEspecial
from .calc_extended import calcula_frete_completo, CalcBreakdownExtended
from .fasthtml import *

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


router = APIRouter()


def normalizar_texto(texto: str) -> str:
    """
    Normaliza texto removendo acentos, convertendo para minúsculas e removendo caracteres especiais
    """
    if not texto:
        return ""

    # Converter para minúsculas
    texto = texto.lower()

    # Remover acentos usando NFD
    texto = unicodedata.normalize('NFD', texto)
    texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')

    # Substituir hífens, barras e outros separadores por espaços
    texto = re.sub(r'[-/\\|_]+', ' ', texto)

    # Remover caracteres especiais, manter apenas letras, números e espaços
    texto = re.sub(r'[^a-z0-9\s]', '', texto)

    # Remover espaços extras
    texto = re.sub(r'\s+', ' ', texto).strip()

    return texto


def criar_termos_busca(termo: str) -> tuple[str, str, str]:
    """
    Cria diferentes variações do termo para busca:
    - original: termo original normalizado
    - inicio: para busca que começa com o termo
    - contem: para busca que contém o termo
    """
    termo_norm = normalizar_texto(termo)

    if not termo_norm:
        return "", "", ""

    termo_inicio = f"{termo_norm}%"
    termo_contem = f"%{termo_norm}%"

    return termo_norm, termo_inicio, termo_contem


def layout_extended(content):
    """Layout base estendido com autocomplete para cidades"""
    return html(
        head(
            meta({"charset": "utf-8"}),
            meta({"name": "viewport", "content": "width=device-width, initial-scale=1"}),
            title("Calculadora de Frete Rodonaves - Versão Completa"),
            link({"rel": "stylesheet", "href": "/static/style.css"}),
            script({"src": "https://unpkg.com/htmx.org@1.9.10"}),
            style({}, """
                * { margin: 0; padding: 0; box-sizing: border-box; }
                body { font-family: system-ui, -apple-system, sans-serif; background: #f5f5f5; padding: 20px; }
                .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                h1 { color: #333; margin-bottom: 10px; }
                .subtitle { color: #666; margin-bottom: 30px; font-size: 14px; }
                .form-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 20px; }
                .form-group { display: flex; flex-direction: column; }
                .form-group label { font-weight: 500; margin-bottom: 5px; color: #555; font-size: 14px; }
                .form-group input, .form-group select { padding: 10px; border: 1px solid #ddd; border-radius: 5px; font-size: 14px; }
                .form-group input:focus, .form-group select:focus { outline: none; border-color: #007bff; }
                .btn { padding: 12px 24px; background: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 14px; font-weight: 500; transition: all 0.3s; }
                .btn:hover { background: #0056b3; }
                .btn:disabled { background: #ccc; cursor: not-allowed; }
                .result-container { margin-top: 30px; padding: 20px; background: #f8f9fa; border-radius: 8px; border: 1px solid #dee2e6; }
                .result-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }
                .result-header h3 { color: #333; }
                .result-total { font-size: 24px; font-weight: bold; color: #28a745; }
                .table-breakdown { width: 100%; margin-top: 15px; }
                .table-breakdown th { text-align: left; padding: 8px; background: #e9ecef; font-size: 13px; }
                .table-breakdown td { padding: 8px; text-align: right; font-size: 13px; }
                .table-breakdown tr.total { font-weight: bold; background: #e9ecef; }
                .table-breakdown tr.hidden { display: none; }
                .table-breakdown tr.taxa-especial { background: #fff3cd; }
                .loading { text-align: center; padding: 20px; color: #666; }
                .error { background: #f8d7da; color: #721c24; padding: 10px; border-radius: 5px; margin-top: 10px; }
                .info { background: #d1ecf1; color: #0c5460; padding: 10px; border-radius: 5px; margin-top: 10px; }
                .warning { background: #fff3cd; color: #856404; padding: 10px; border-radius: 5px; margin-top: 10px; }

                /* Autocomplete styles */
                .autocomplete { position: relative; }
                .autocomplete-items { position: absolute; background: white; border: 1px solid #ddd; border-top: none; z-index: 99; top: 100%; left: 0; right: 0; max-height: 300px; overflow-y: auto; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
                .autocomplete-items div { padding: 10px; cursor: pointer; border-bottom: 1px solid #f0f0f0; }
                .autocomplete-items div:hover { background: #f8f9fa; }
                .autocomplete-items div strong { color: #007bff; }
                .autocomplete-items .categoria { font-size: 11px; color: #666; margin-left: 10px; }
                .autocomplete-items .taxa { display: inline-block; padding: 2px 6px; background: #ff6b6b; color: white; border-radius: 3px; font-size: 10px; margin-left: 5px; }

                .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px; }
                .stat-card { background: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 4px solid #007bff; }
                .stat-card h4 { font-size: 12px; color: #666; margin-bottom: 5px; }
                .stat-card .value { font-size: 20px; font-weight: bold; color: #333; }

                .htmx-indicator { display: none; }
                .htmx-request .htmx-indicator { display: inline; }
                .htmx-request.btn { pointer-events: none; opacity: 0.7; }
            """)
        ),
        body({}, content)
    )


@router.get("/extended", response_class=HTMLResponse)
async def home_extended():
    """Página inicial com interface estendida"""

    with Session(engine) as session:
        # Buscar produtos
        produtos = session.exec(select(Produto)).all()

        # Estatísticas do sistema - com fallback automático
        # Tentar CidadeRodonaves primeiro, depois Destino
        rodonaves_cities = session.exec(select(CidadeRodonaves)).all()
        if rodonaves_cities:
            # Usar dados da tabela CidadeRodonaves (sistema completo)
            total_cidades = len(rodonaves_cities)
            cidades_com_tda = len(session.exec(select(CidadeRodonaves).where(
                CidadeRodonaves.categoria_tarifa.in_(["CAPITAL", "INTERIOR_1"])
            )).all())
            cidades_com_trt = len(session.exec(select(CidadeRodonaves).where(
                CidadeRodonaves.categoria_tarifa == "INTERIOR_2"
            )).all())
        else:
            # Fallback para tabela Destino (sistema simples)
            destino_cities = session.exec(select(Destino)).all()
            total_cidades = len(destino_cities)
            cidades_com_tda = len(session.exec(select(Destino).where(
                Destino.categoria.in_(["CAPITAL", "INTERIOR_1"])
            )).all())
            cidades_com_trt = len(session.exec(select(Destino).where(
                Destino.categoria == "INTERIOR_2"
            )).all())
        estados_cobertos = len(session.exec(select(Estado)).all())

    return layout_extended(
        div({"class": "container"},
            h1({}, "Calculadora de Frete Rodonaves"),

            # Estatísticas
            div({"class": "stats-grid"},
                div({"class": "stat-card"},
                    h4({}, "Cidades Atendidas"),
                    div({"class": "value"}, f"{total_cidades:,}")
                ),
                div({"class": "stat-card"},
                    h4({}, "Estados"),
                    div({"class": "value"}, str(estados_cobertos))
                ),
                div({"class": "stat-card"},
                    h4({}, "Cidades com TDA"),
                    div({"class": "value"}, str(cidades_com_tda))
                ),
                div({"class": "stat-card"},
                    h4({}, "Cidades com TRT"),
                    div({"class": "value"}, str(cidades_com_trt))
                )
            ),

            # Formulário
            form({"hx-post": "/extended/calcular", "hx-target": "#resultado"},
                div({"class": "form-grid"},
                    # Produto
                    div({"class": "form-group"},
                        label({"for": "produto_id"}, "Produto"),
                        select_({"name": "produto_id", "id": "produto_id", "required": True},
                            option({"value": ""}, "Selecione um produto"),
                            *[option({"value": str(p.id)}, p.nome)
                              for p in produtos]
                        )
                    ),

                    # Estado
                    div({"class": "form-group"},
                        label({"for": "estado"}, "Estado"),
                        select_({"name": "estado", "id": "estado", "required": True,
                                "hx-get": "/extended/cidades", "hx-target": "#cidade-container",
                                "hx-trigger": "change"},
                            option({"value": ""}, "Selecione o estado"),
                            option({"value": "SP"}, "São Paulo"),
                            option({"value": "RJ"}, "Rio de Janeiro"),
                            option({"value": "MG"}, "Minas Gerais"),
                            option({"value": "ES"}, "Espírito Santo"),
                            option({"value": "PR"}, "Paraná"),
                            option({"value": "SC"}, "Santa Catarina"),
                            option({"value": "RS"}, "Rio Grande do Sul"),
                            option({"value": "GO"}, "Goiás"),
                            option({"value": "DF"}, "Distrito Federal"),
                            option({"value": "MS"}, "Mato Grosso do Sul"),
                            option({"value": "MT"}, "Mato Grosso")
                        )
                    ),

                    # Cidade (será preenchida via HTMX)
                    div({"class": "form-group", "id": "cidade-container"},
                        label({"for": "cidade_id"}, "Cidade"),
                        input_({"type": "text", "name": "cidade_busca", "id": "cidade_busca",
                               "placeholder": "Selecione o estado primeiro", "disabled": True})
                    ),

                    # Valor NF
                    div({"class": "form-group"},
                        label({"for": "valor_nf"}, "Valor da NF (R$)"),
                        input_({"type": "number", "name": "valor_nf", "id": "valor_nf",
                               "step": "0.01", "min": "0", "placeholder": "Opcional"})
                    )
                ),

                button({"type": "submit", "class": "btn"},
                    span({"class": "htmx-indicator"}, "Calculando... "),
                    "Calcular Frete"
                )
            ),

            # Container para resultado
            div({"id": "resultado"})
        )
    )


@router.get("/extended/cidades", response_class=HTMLResponse)
async def buscar_cidades(estado: str):
    """
    Retorna campo de busca de cidades para o estado selecionado
    Com busca case-insensitive e validação robusta
    """

    logger.info(f"[BUSCAR_CIDADES] Requisição para estado: '{estado}'")

    try:
        if not estado or not estado.strip():
            logger.info("[BUSCAR_CIDADES] Estado não fornecido ou vazio")
            return div({"class": "form-group"},
                label({"for": "cidade_busca"}, "Cidade"),
                input_({"type": "text", "name": "cidade_busca", "id": "cidade_busca",
                       "placeholder": "Selecione o estado primeiro", "disabled": True})
            )

        # Normalizar estado
        estado_norm = estado.strip().upper()
        logger.info(f"[BUSCAR_CIDADES] Estado normalizado: '{estado_norm}'")

        # Validar se o estado existe no banco
        with Session(engine) as session:
            estado_obj = session.exec(
                select(Estado).where(Estado.sigla.ilike(estado_norm))
            ).first()

            if not estado_obj:
                logger.warning(f"[BUSCAR_CIDADES] Estado não encontrado: '{estado_norm}'")
                # Buscar estados disponíveis
                estados_disponiveis = session.exec(select(Estado.sigla)).all()
                logger.info(f"[BUSCAR_CIDADES] Estados disponíveis: {estados_disponiveis}")

                return div({"class": "form-group"},
                    label({"for": "cidade_busca"}, "Cidade"),
                    input_({"type": "text", "name": "cidade_busca", "id": "cidade_busca",
                           "placeholder": f"Estado '{estado_norm}' inválido", "disabled": True}),
                    div({"class": "error", "style": "font-size: 12px; margin-top: 5px;"},
                        f"Estado '{estado_norm}' não encontrado. Disponíveis: {', '.join(estados_disponiveis)}")
                )

            logger.info(f"[BUSCAR_CIDADES] Estado válido encontrado: {estado_obj.sigla} - {estado_obj.nome}")

        # Campo de busca funcional
        return div({"class": "form-group autocomplete"},
            label({"for": "cidade_busca"}, "Cidade"),
            input_({"type": "text", "name": "cidade_busca", "id": "cidade_busca",
                   "placeholder": f"Digite o nome da cidade de {estado_obj.sigla}...",
                   "hx-get": f"/extended/autocomplete?estado={estado_norm}",
                   "hx-trigger": "keyup changed delay:300ms",
                   "hx-target": "#cidade-suggestions",
                   "hx-include": "[name='cidade_busca']",
                   "autocomplete": "off"}),
            input_({"type": "hidden", "name": "cidade_id", "id": "cidade_id"}),
            div({"id": "cidade-suggestions", "class": "autocomplete-items"})
        )

    except Exception as e:
        logger.error(f"[BUSCAR_CIDADES] Erro fatal: {e}")
        logger.exception("Stack trace completo:")

        return div({"class": "form-group"},
            label({"for": "cidade_busca"}, "Cidade"),
            input_({"type": "text", "name": "cidade_busca", "id": "cidade_busca",
                   "placeholder": "Erro interno. Verifique os logs.", "disabled": True}),
            div({"class": "error", "style": "font-size: 12px; margin-top: 5px;"},
                f"Erro interno ao carregar cidades. Estado: '{estado}'")
        )


@router.get("/extended/autocomplete", response_class=HTMLResponse)
async def autocomplete_cidades(
    estado: str,
    q: str = Query("", alias="cidade_busca")
):
    """
    Autocomplete COMPLETAMENTE ROBUSTO para busca de cidades

    Funcionalidades:
    - Busca case-insensitive
    - Normalização de texto (remove acentos)
    - Múltiplas estratégias de busca
    - Logs detalhados para debug
    - Tratamento robusto de erros
    """

    # Log inicial da requisição
    logger.info(f"[AUTOCOMPLETE] Iniciando busca: estado='{estado}', termo='{q}'")

    try:
        # Validação inicial do input
        if not estado:
            logger.warning("[AUTOCOMPLETE] Estado não fornecido")
            return div({"class": "error"}, "Estado é obrigatório")

        if not q or len(q.strip()) < 2:
            logger.info(f"[AUTOCOMPLETE] Termo muito curto: '{q}' (min: 2 caracteres)")
            return ""

        # Normalizar entradas
        estado_norm = estado.strip().upper()
        termo_original = q.strip()

        logger.info(f"[AUTOCOMPLETE] Inputs normalizados: estado='{estado_norm}', termo='{termo_original}'")

        # Preparar termos de busca
        termo_norm, termo_inicio, termo_contem = criar_termos_busca(termo_original)

        if not termo_norm:
            logger.warning(f"[AUTOCOMPLETE] Termo normalizado resultou vazio: '{termo_original}'")
            return div({}, "Termo de busca inválido")

        logger.info(f"[AUTOCOMPLETE] Termos de busca: normalizado='{termo_norm}', inicio='{termo_inicio}', contem='{termo_contem}'")

        with Session(engine) as session:
            # Detectar qual tabela usar (CidadeRodonaves vs Destino)
            rodonaves_count = len(session.exec(select(CidadeRodonaves)).all())
            use_extended = rodonaves_count > 0

            logger.info(f"[AUTOCOMPLETE] Sistema detectado: {'CidadeRodonaves' if use_extended else 'Destino'} ({rodonaves_count if use_extended else 'fallback'})")

            # Buscar estado com busca case-insensitive
            logger.info(f"[AUTOCOMPLETE] Buscando estado: '{estado_norm}'")

            estado_obj = session.exec(
                select(Estado).where(Estado.sigla.ilike(estado_norm))
            ).first()

            if not estado_obj:
                logger.error(f"[AUTOCOMPLETE] Estado não encontrado: '{estado_norm}'")
                # Buscar estados disponíveis para debug
                estados_disponiveis = session.exec(select(Estado.sigla)).all()
                logger.info(f"[AUTOCOMPLETE] Estados disponíveis: {estados_disponiveis}")
                return div({"class": "error"}, f"Estado '{estado_norm}' não encontrado")

            logger.info(f"[AUTOCOMPLETE] Estado encontrado: {estado_obj.sigla} - {estado_obj.nome}")

            # Estratégia 1: Busca exata normalizada (mais prioritária)
            logger.info("[AUTOCOMPLETE] Estratégia 1: Busca exata normalizada")

            if use_extended:
                # Sistema completo: CidadeRodonaves
                cidades_exatas = session.exec(
                    select(CidadeRodonaves)
                    .join(Estado, CidadeRodonaves.estado_id == Estado.id)
                    .where(
                        and_(
                            Estado.sigla == estado_norm,
                            CidadeRodonaves.nome.ilike(termo_original)
                        )
                    )
                    .limit(5)
                ).all()
            else:
                # Sistema simples: Destino
                cidades_exatas = session.exec(
                    select(Destino)
                    .where(
                        and_(
                            Destino.uf == estado_norm,
                            Destino.cidade.ilike(termo_original)
                        )
                    )
                    .limit(5)
                ).all()

            logger.info(f"[AUTOCOMPLETE] Estratégia 1 - Encontradas {len(cidades_exatas)} cidades exatas")

            # Estratégia 2: Busca por início (case-insensitive)
            logger.info("[AUTOCOMPLETE] Estratégia 2: Busca por início")

            if use_extended:
                # Sistema completo: CidadeRodonaves
                cidades_inicio = session.exec(
                    select(CidadeRodonaves)
                    .join(Estado, CidadeRodonaves.estado_id == Estado.id)
                    .where(
                        and_(
                            Estado.sigla == estado_norm,
                            CidadeRodonaves.nome.ilike(f"{termo_original}%")
                        )
                    )
                    .limit(15)
                ).all()
            else:
                # Sistema simples: Destino
                cidades_inicio = session.exec(
                    select(Destino)
                    .where(
                        and_(
                            Destino.uf == estado_norm,
                            Destino.cidade.ilike(f"{termo_original}%")
                        )
                    )
                    .limit(15)
                ).all()

            logger.info(f"[AUTOCOMPLETE] Estratégia 2 - Encontradas {len(cidades_inicio)} cidades por início")

            # Estratégia 3: Busca por conteúdo (case-insensitive)
            logger.info("[AUTOCOMPLETE] Estratégia 3: Busca por conteúdo")

            if use_extended:
                # Sistema completo: CidadeRodonaves
                cidades_contem = session.exec(
                    select(CidadeRodonaves)
                    .join(Estado, CidadeRodonaves.estado_id == Estado.id)
                    .where(
                        and_(
                            Estado.sigla == estado_norm,
                            CidadeRodonaves.nome.ilike(f"%{termo_original}%")
                        )
                    )
                    .limit(20)
                ).all()
            else:
                # Sistema simples: Destino
                cidades_contem = session.exec(
                    select(Destino)
                    .where(
                        and_(
                            Destino.uf == estado_norm,
                            Destino.cidade.ilike(f"%{termo_original}%")
                        )
                    )
                    .limit(20)
                ).all()

            logger.info(f"[AUTOCOMPLETE] Estratégia 3 - Encontradas {len(cidades_contem)} cidades por conteúdo")

            # Combinar resultados removendo duplicatas (manter ordem de prioridade)
            cidades_encontradas = []
            ids_ja_adicionados = set()

            # Adicionar por ordem de prioridade
            for lista_cidades in [cidades_exatas, cidades_inicio, cidades_contem]:
                for cidade in lista_cidades:
                    if cidade.id not in ids_ja_adicionados:
                        cidades_encontradas.append(cidade)
                        ids_ja_adicionados.add(cidade.id)

                        # Limitar a 20 resultados totais
                        if len(cidades_encontradas) >= 20:
                            break

                if len(cidades_encontradas) >= 20:
                    break

            logger.info(f"[AUTOCOMPLETE] Total de cidades encontradas (sem duplicatas): {len(cidades_encontradas)}")

            # Estratégia 4: Se ainda não encontrou nada, busca mais flexível
            if not cidades_encontradas:
                logger.info("[AUTOCOMPLETE] Estratégia 4: Busca flexível (palavras individuais)")

                # Quebrar termo em palavras e buscar cada uma
                palavras = termo_norm.split()
                if len(palavras) > 1:
                    # Buscar cidades que contenham qualquer uma das palavras
                    condicoes_palavras = []
                    for palavra in palavras:
                        if len(palavra) >= 2:  # Só palavras com 2+ caracteres
                            if use_extended:
                                condicoes_palavras.append(CidadeRodonaves.nome.ilike(f"%{palavra}%"))
                            else:
                                condicoes_palavras.append(Destino.cidade.ilike(f"%{palavra}%"))

                    if condicoes_palavras:
                        if use_extended:
                            # Sistema completo: CidadeRodonaves
                            cidades_flexivel = session.exec(
                                select(CidadeRodonaves)
                                .join(Estado, CidadeRodonaves.estado_id == Estado.id)
                                .where(
                                    and_(
                                        Estado.sigla == estado_norm,
                                        or_(*condicoes_palavras)
                                    )
                                )
                                .limit(15)
                            ).all()
                        else:
                            # Sistema simples: Destino
                            cidades_flexivel = session.exec(
                                select(Destino)
                                .where(
                                    and_(
                                        Destino.uf == estado_norm,
                                        or_(*condicoes_palavras)
                                    )
                                )
                                .limit(15)
                            ).all()

                        cidades_encontradas.extend(cidades_flexivel)
                        logger.info(f"[AUTOCOMPLETE] Estratégia 4 - Encontradas {len(cidades_flexivel)} cidades flexível")

            # Verificar se encontrou alguma cidade
            if not cidades_encontradas:
                logger.warning(f"[AUTOCOMPLETE] Nenhuma cidade encontrada para '{termo_original}' no estado '{estado_norm}'")

                # Buscar algumas cidades do estado para debug
                if use_extended:
                    amostra_cidades = session.exec(
                        select(CidadeRodonaves.nome)
                        .join(Estado, CidadeRodonaves.estado_id == Estado.id)
                        .where(Estado.sigla == estado_norm)
                        .limit(5)
                    ).all()
                else:
                    amostra_cidades = session.exec(
                        select(Destino.cidade)
                        .where(Destino.uf == estado_norm)
                        .limit(5)
                    ).all()

                logger.info(f"[AUTOCOMPLETE] Amostra de cidades disponíveis no estado: {amostra_cidades}")

                return div({}, "Nenhuma cidade encontrada")

            # Gerar HTML das sugestões
            logger.info(f"[AUTOCOMPLETE] Gerando HTML para {len(cidades_encontradas)} cidades")

            items = []
            for i, cidade in enumerate(cidades_encontradas):
                try:
                    # Acesso universal aos campos (CidadeRodonaves vs Destino)
                    if use_extended:
                        cidade_nome = cidade.nome
                        cidade_categoria = cidade.categoria_tarifa
                    else:
                        cidade_nome = cidade.cidade
                        cidade_categoria = getattr(cidade, 'categoria', 'N/A')

                    # Escape de aspas simples no nome da cidade para JavaScript
                    nome_escaped = cidade_nome.replace("'", "\\'")

                    onclick = f"document.getElementById('cidade_busca').value='{nome_escaped}'; "
                    onclick += f"document.getElementById('cidade_id').value='{cidade.id}'; "
                    onclick += "document.getElementById('cidade-suggestions').innerHTML='';"

                    # Destacar termo buscado no nome
                    nome_destacado = cidade_nome
                    try:
                        # Destacar termo original (case-insensitive)
                        padrao = re.compile(re.escape(termo_original), re.IGNORECASE)
                        nome_destacado = padrao.sub(lambda m: f"<strong>{m.group(0)}</strong>", cidade_nome)
                    except Exception as e:
                        logger.warning(f"[AUTOCOMPLETE] Erro ao destacar termo em '{cidade_nome}': {e}")
                        nome_destacado = cidade_nome

                    # Taxas especiais
                    taxas = []
                    if False:
                        taxas.append(span({"class": "taxa"}, "TDA"))
                    if False:
                        taxas.append(span({"class": "taxa"}, "TRT"))

                    # Log detalhado da cidade
                    logger.debug(f"[AUTOCOMPLETE] Cidade {i+1}: {cidade_nome} (ID: {cidade.id}, Cat: {cidade_categoria}, TDA: {False}, TRT: {False})")

                    items.append(
                        div({"onclick": onclick, "style": "cursor: pointer;"},
                            # Usar innerHTML seguro
                            span({}, cidade_nome),  # Não usar HTML raw aqui
                            span({"class": "categoria"}, f"({cidade_categoria})"),
                            *taxas
                        )
                    )

                except Exception as e:
                    cidade_nome_fallback = getattr(cidade, 'nome', getattr(cidade, 'cidade', 'Unknown'))
                    logger.error(f"[AUTOCOMPLETE] Erro ao processar cidade {cidade_nome_fallback}: {e}")
                    continue

            logger.info(f"[AUTOCOMPLETE] Busca concluída com sucesso: {len(items)} itens gerados")

            return div({}, *items)

    except Exception as e:
        logger.error(f"[AUTOCOMPLETE] Erro fatal na busca: {e}")
        logger.exception("Stack trace completo:")

        return div({"class": "error"},
                  f"Erro interno na busca. Verifique os logs. (Termo: '{q}', Estado: '{estado}')")


@router.post("/extended/calcular", response_class=HTMLResponse)
async def calcular_frete_extended(
    produto_id: int = Form(...),
    cidade_id: int = Form(...),
    valor_nf: Optional[float] = Form(None)
):
    """Calcula frete com taxas especiais"""

    # Calcular frete completo
    resultado = calcula_frete_completo(produto_id, cidade_id, valor_nf)

    if not resultado:
        return div({"class": "result-container"},
            div({"class": "error"}, "Erro ao calcular frete. Verifique os dados informados.")
        )

    # Buscar informações adicionais
    with Session(engine) as session:
        cidade = session.get(CidadeRodonaves, cidade_id)
        produto = session.get(Produto, produto_id)

        # Load related data within session to avoid DetachedInstanceError
        # Acesso universal aos campos da cidade
        if cidade:
            cidade_nome = getattr(cidade, 'nome', getattr(cidade, 'cidade', 'Desconhecida'))
            cidade_categoria = getattr(cidade, 'categoria_tarifa', getattr(cidade, 'categoria', 'Desconhecida'))
            estado_sigla = cidade.estado.sigla if hasattr(cidade, 'estado') and cidade.estado else getattr(cidade, 'uf', '??')
        else:
            cidade_nome = "Desconhecida"
            cidade_categoria = "Desconhecida"
            estado_sigla = "??"
        produto_nome = produto.nome if produto else "Desconhecido"

    # Gerar HTML do resultado
    return div({"class": "result-container"},
        div({"class": "result-header"},
            h3({}, f"Frete para {cidade_nome}/{estado_sigla}"),
            div({"class": "result-total"}, f"Total Frete Rodonaves: R$ {resultado.total:.2f}")
        ),

        # Informações do cálculo
        div({"class": "info"},
            f"Produto: {produto_nome} | ",
            f"Peso Real: {resultado.peso_real_kg}kg | ",
            f"Peso Cubado: {resultado.peso_cubado}kg | ",
            f"Peso Taxável: {resultado.peso_taxavel}kg | ",
            f"Categoria: {cidade_categoria}"
        ),

        # Prazo de entrega
        div({"class": "info", "style": "background: #d4edda; border-color: #c3e6cb; color: #155724; margin-top: 10px;"},
            f"📦 Prazo de Entrega: {resultado.prazo_formatado}" if resultado.prazo_formatado else "📦 Prazo de Entrega: Consulte",
            f" ({resultado.tipo_transporte})" if resultado.tipo_transporte and resultado.tipo_transporte == "FLUVIAL" else ""
        ),

        # Breakdown detalhado
        table({"class": "table-breakdown"},
            tbody({},
                tr({},
                    th({}, "Base (faixa de peso)"),
                    td({}, f"R$ {resultado.base_faixa:.2f}")
                ),

                # Excedente (se houver)
                tr({"class": "hidden" if resultado.excedente_valor == 0 else ""},
                    th({}, f"Excedente ({resultado.excedente_kg}kg)"),
                    td({}, f"R$ {resultado.excedente_valor:.2f}")
                ) if resultado.excedente_valor > 0 else "",

                tr({},
                    th({}, "Pedágio"),
                    td({}, f"R$ {resultado.pedagio:.2f}")
                ),

                tr({},
                    th({}, "Frete-valor (F-valor)"),
                    td({}, f"R$ {resultado.fvalor:.2f}")
                ),

                tr({},
                    th({}, "GRIS"),
                    td({}, f"R$ {resultado.gris:.2f}")
                ),

                tr({},
                    th({}, "ICMS (12%)"),
                    td({}, f"R$ {resultado.icms:.2f}")
                ),

                # TDA (se houver)
                tr({"class": "taxa-especial"} if resultado.tda > 0 else {"class": "hidden"},
                    th({}, f"TDA - Taxa Dificuldade Acesso"),
                    td({}, f"R$ {resultado.tda:.2f}")
                ) if resultado.tda > 0 else "",

                # TRT (se houver)
                tr({"class": "taxa-especial"} if resultado.trt > 0 else {"class": "hidden"},
                    th({}, f"TRT - Taxa Restrição Trânsito"),
                    td({}, f"R$ {resultado.trt:.2f}")
                ) if resultado.trt > 0 else "",

                # Total Frete
                tr({"class": "total"},
                    th({}, "TOTAL FRETE RODONAVES"),
                    td({}, f"R$ {resultado.total:.2f}")
                ),

                # Valor Embalagem
                tr({},
                    th({}, f"Valor Embalagem ({resultado.produto_nome})"),
                    td({}, f"R$ {resultado.valor_embalagem:.2f}")
                ),

                # Total Geral
                tr({"class": "total", "style": "background: #28a745; color: black; font-weight: bold;"},
                    th({}, "VALOR TOTAL (Frete + Embalagem)"),
                    td({}, f"R$ {resultado.total_com_embalagem:.2f}")
                )
            )
        ),

        # Avisos sobre taxas especiais
        div({"class": "warning"},
            f"⚠️ Esta cidade possui taxas especiais: {resultado.justificativa_taxas}"
        ) if resultado.justificativa_taxas else ""
    )


@router.get("/extended/stats", response_class=HTMLResponse)
async def estatisticas():
    """Página de estatísticas do sistema"""

    with Session(engine) as session:
        # Estatísticas gerais - com fallback automático
        rodonaves_cities = session.exec(select(CidadeRodonaves)).all()
        if rodonaves_cities:
            # Usar dados da tabela CidadeRodonaves (sistema completo)
            total_cidades = len(rodonaves_cities)
            capitais = len(session.exec(
                select(CidadeRodonaves).where(CidadeRodonaves.categoria_tarifa == "CAPITAL")
            ).all())
            interior1 = len(session.exec(
                select(CidadeRodonaves).where(CidadeRodonaves.categoria_tarifa == "INTERIOR_1")
            ).all())
            interior2 = len(session.exec(
                select(CidadeRodonaves).where(CidadeRodonaves.categoria_tarifa == "INTERIOR_2")
            ).all())
        else:
            # Fallback para tabela Destino (sistema simples)
            destino_cities = session.exec(select(Destino)).all()
            total_cidades = len(destino_cities)
            capitais = len(session.exec(
                select(Destino).where(Destino.categoria == "CAPITAL")
            ).all())
            interior1 = len(session.exec(
                select(Destino).where(Destino.categoria == "INTERIOR_1")
            ).all())
            interior2 = len(session.exec(
                select(Destino).where(Destino.categoria == "INTERIOR_2")
            ).all())

        total_estados = len(session.exec(select(Estado)).all())
        total_produtos = len(session.exec(select(Produto)).all())
        total_taxas = len(session.exec(select(TaxaEspecial)).all())

        # Top estados
        estados = session.exec(
            select(Estado).join(CidadeRodonaves)
        ).all()

    return layout_extended(
        div({"class": "container"},
            h1({}, "Estatísticas do Sistema"),

            div({"class": "stats-grid"},
                div({"class": "stat-card"},
                    h4({}, "Total de Cidades"),
                    div({"class": "value"}, f"{total_cidades:,}")
                ),
                div({"class": "stat-card"},
                    h4({}, "Estados Cobertos"),
                    div({"class": "value"}, str(total_estados))
                ),
                div({"class": "stat-card"},
                    h4({}, "Produtos Cadastrados"),
                    div({"class": "value"}, str(total_produtos))
                ),
                div({"class": "stat-card"},
                    h4({}, "Taxas Especiais"),
                    div({"class": "value"}, str(total_taxas))
                )
            ),

            h3({}, "Categorização de Cidades"),
            div({"class": "stats-grid"},
                div({"class": "stat-card"},
                    h4({}, "Capitais"),
                    div({"class": "value"}, str(capitais))
                ),
                div({"class": "stat-card"},
                    h4({}, "Interior 1"),
                    div({"class": "value"}, str(interior1))
                ),
                div({"class": "stat-card"},
                    h4({}, "Interior 2"),
                    div({"class": "value"}, str(interior2))
                )
            )
        )
    )