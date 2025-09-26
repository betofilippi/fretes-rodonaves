from fastapi import APIRouter, Depends, UploadFile, Form, File, HTTPException
from fastapi.responses import HTMLResponse
from sqlmodel import Session, select
from typing import List, Optional
import os
import shutil
from datetime import datetime

from .db import get_session
from .models import (
    Produto, VersaoTabela, TarifaPeso, ParametrosGerais,
    Destino, CorredorKM, MapDestinoCorredor
)
from .calc import calcula_frete, CalcInput, ParamSet, Tarifa
# Temporariamente desabilitado - requer pdfplumber
# from .parsers import parse_pdf_tabela, extract_corredor_data_from_cte
from .fasthtml import (
    html, head, body, title, meta, link, script, div, h1, h2, h3, h4, h5,
    form, input_, select_, option, button, table, thead, tbody, tr, th, td,
    container, row, col, card, form_group, alert, nav_link, label,
    produto_select, destino_select, breakdown_table, htmx_form, loading_indicator
)

router = APIRouter()

import os
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "data", "uploads")


@router.get("/", response_class=HTMLResponse)
def home(session: Session = Depends(get_session)):
    """Página principal com calculadora de frete"""
    # Buscar produtos e destinos
    produtos = session.exec(select(Produto)).all()
    destinos = session.exec(select(Destino)).all()

    # Gerar options para produtos
    produtos_options = ""
    for produto in produtos:
        produtos_options += f'<option value="{produto.id}">{produto.nome} ({produto.largura_cm}×{produto.altura_cm}×{produto.profundidade_cm}cm - {produto.peso_real_kg}kg)</option>\n'

    # Gerar options para destinos
    destinos_options = ""
    for destino in destinos:
        destinos_options += f'<option value="{destino.id}">{destino.cidade}/{destino.uf} ({destino.categoria})</option>\n'

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Calculadora de Frete - Rodonaves</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link rel="stylesheet" href="/static/styles.css">
        <script src="/static/htmx.min.js"></script>
    </head>
    <body>
        <div class="container">
            <h1 class="text-center mb-4">Calculadora de Frete — Rodonaves</h1>

            <div class="nav-menu mb-4">
                <a href="/" class="nav-link active">Calculadora</a>
                <a href="/produtos" class="nav-link">Produtos</a>
                <a href="/versoes" class="nav-link">Versões</a>
            </div>

            <div class="row">
                <div class="col-6">
                    <div class="card mb-4">
                        <h3>Calcular Frete</h3>
                        <form hx-post="/cotacao" hx-target="#resultado" hx-on::submit="this.querySelector('button[type=submit]').innerHTML = 'Calculando...'; this.querySelector('button[type=submit]').disabled = true;">
                            <div class="form-group">
                                <label for="produto_id">Produto:</label>
                                <select name="produto_id" required id="produto_id" hx-on:change="updateValorNF(this)">
                                    <option value="">Selecione um produto</option>
                                    {produtos_options}
                                </select>
                            </div>

                            <div class="form-group">
                                <label for="destino_id">Destino:</label>
                                <select name="destino_id" required id="destino_id">
                                    <option value="">Selecione um destino</option>
                                    {destinos_options}
                                </select>
                            </div>

                            <div class="form-group">
                                <label for="valor_nf">Valor da NF (R$):</label>
                                <input type="number" name="valor_nf" id="valor_nf" step="0.01" placeholder="0.00" required>
                                <small class="text-muted">Valor dos produtos para cálculo de seguro e taxas</small>
                            </div>

                            <div class="text-center">
                                <button type="submit" class="btn btn-primary">Calcular Frete</button>
                            </div>
                        </form>
                    </div>
                </div>

                <div class="col-6">
                    <div id="resultado" class="result-area">
                        <div class="text-muted text-center">
                            <p>📦 <strong>Selecione um produto e destino</strong></p>
                            <p>Preencha os dados e clique em 'Calcular Frete' para ver:</p>
                            <ul style="text-align: left; display: inline-block;">
                                <li>Peso cubado vs real</li>
                                <li>Base por faixa + excedente</li>
                                <li>Pedágio, F-valor e GRIS</li>
                                <li>ICMS e total final</li>
                            </ul>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <script>
            // Dados dos produtos para auto-preenchimento
            const produtosData = {{
                {chr(10).join([f'"{p.id}": {{"valor_nf_padrao": {p.valor_nf_padrao}}},' for p in produtos])}
            }};

            function updateValorNF(selectElement) {{
                const produtoId = selectElement.value;
                const valorNFInput = document.getElementById('valor_nf');

                if (produtoId && produtosData[produtoId]) {{
                    valorNFInput.value = produtosData[produtoId].valor_nf_padrao.toFixed(2);
                }} else {{
                    valorNFInput.value = '';
                }}
            }}

            // Resetar botão após resposta HTMX
            document.body.addEventListener('htmx:afterSwap', function() {{
                const submitBtn = document.querySelector('button[type=submit]');
                submitBtn.innerHTML = 'Calcular Frete';
                submitBtn.disabled = false;
            }});
        </script>
    </body>
    </html>
    """


@router.post("/cotacao", response_class=HTMLResponse)
def cotacao(
    produto_id: int = Form(...),
    destino_id: int = Form(...),
    valor_nf: float = Form(...),
    session: Session = Depends(get_session)
):
    """Calcular frete e retornar breakdown"""
    try:
        # Buscar dados
        produto = session.get(Produto, produto_id)
        destino = session.get(Destino, destino_id)

        if not produto or not destino:
            return alert("Produto ou destino não encontrado", "error")

        # Versão ativa
        versao = session.exec(
            select(VersaoTabela).where(VersaoTabela.ativa == True).order_by(VersaoTabela.vigente_desde.desc())
        ).first()

        if not versao:
            return alert("Nenhuma versão de tabela ativa encontrada", "warning")

        # Buscar tarifa e parâmetros
        tarifa_row = session.exec(
            select(TarifaPeso).where(
                TarifaPeso.versao_id == versao.id,
                TarifaPeso.categoria == destino.categoria
            )
        ).first()

        params_row = session.exec(
            select(ParametrosGerais).where(ParametrosGerais.versao_id == versao.id)
        ).first()

        if not tarifa_row or not params_row:
            return alert("Tarifa ou parâmetros não encontrados para este destino", "warning")

        # Verificar corredor KM
        corredor_map = session.exec(
            select(MapDestinoCorredor).where(MapDestinoCorredor.destino_id == destino.id)
        ).first()

        corredor = None
        if corredor_map:
            corredor = session.get(CorredorKM, corredor_map.corredor_id)

        # Montar objetos para cálculo
        tarifa = Tarifa(
            ate_10=tarifa_row.ate_10,
            ate_20=tarifa_row.ate_20,
            ate_40=tarifa_row.ate_40,
            ate_60=tarifa_row.ate_60,
            ate_100=tarifa_row.ate_100,
            excedente_por_kg=tarifa_row.excedente_por_kg
        )

        params = ParamSet(
            cubagem_kg_por_m3=params_row.cubagem_kg_por_m3,
            fvalor_percent_padrao=params_row.fvalor_percent_padrao,
            fvalor_min=params_row.fvalor_min,
            gris_percent_ate_10k=params_row.gris_percent_ate_10k,
            gris_percent_acima_10k=params_row.gris_percent_acima_10k,
            gris_min=params_row.gris_min,
            pedagio_por_100kg=params_row.pedagio_por_100kg,
            icms_percent=params_row.icms_percent
        )

        inp = CalcInput(
            largura_cm=produto.largura_cm,
            altura_cm=produto.altura_cm,
            profundidade_cm=produto.profundidade_cm,
            peso_real_kg=produto.peso_real_kg,
            valor_nf=valor_nf,
            categoria_destino=destino.categoria,
            corredor_f=corredor.fator_multiplicador if corredor else None,
            pedagio_pracas=corredor.pedagio_pracas if corredor else None,
            fvalor_percent_override=corredor.fvalor_percent_override if corredor else None
        )

        # Calcular
        resultado = calcula_frete(inp, tarifa, params)

        # Retornar resultado
        return f"""
        <div class="card result-card">
            <h3 class="text-success">✅ Resultado do Cálculo</h3>

            <div class="product-info mb-3">
                <h5>Produto: {produto.nome}</h5>
                <div class="text-muted">Destino: {destino.cidade}/{destino.uf} ({destino.categoria})</div>
                <div class="text-muted">Valor NF: R$ {valor_nf:.2f}</div>
            </div>

            <table class="table table-breakdown">
                <tbody>
                    <tr><th>Peso cubado</th><td>{resultado.peso_cubado} kg</td></tr>
                    <tr><th>Peso taxável</th><td>{resultado.peso_taxavel} kg</td></tr>
                    <tr><th>Base (até 100kg)</th><td>R$ {resultado.base_faixa:.2f}</td></tr>
                    <tr class="{'hidden' if resultado.excedente_valor == 0 else ''}">
                        <th>Excedente</th><td>R$ {resultado.excedente_valor:.2f}</td>
                    </tr>
                    <tr><th>Pedágio</th><td>R$ {resultado.pedagio:.2f}</td></tr>
                    <tr><th>Frete-valor</th><td>R$ {resultado.fvalor:.2f}</td></tr>
                    <tr><th>GRIS</th><td>R$ {resultado.gris:.2f}</td></tr>
                    <tr><th>ICMS</th><td>R$ {resultado.icms:.2f}</td></tr>
                    <tr class="total"><th>TOTAL</th><td>R$ {resultado.total:.2f}</td></tr>
                </tbody>
            </table>

            <div class="text-center mt-3">
                <button class="btn btn-secondary" onclick="window.print()">🖨️ Imprimir</button>
                <button class="btn btn-primary" onclick="location.reload()">🔄 Nova Cotação</button>
            </div>
        </div>
        """

    except Exception as e:
        return f'<div class="alert alert-error">❌ Erro no cálculo: {str(e)}</div>'


@router.get("/produtos", response_class=HTMLResponse)
def listar_produtos(session: Session = Depends(get_session)):
    """Lista produtos cadastrados"""
    produtos = session.exec(select(Produto)).all()

    content = container(
        h2({}, "Produtos Cadastrados"),
        div({"class": "mb-3"},
            button({"class": "btn btn-primary", "hx-get": "/produtos/form", "hx-target": "#form-area"},
                "Novo Produto"
            )
        ),
        div({"id": "form-area"}),
        table({"class": "table table-striped"},
            thead({},
                tr({},
                    th({}, "Nome"),
                    th({}, "Dimensões (cm)"),
                    th({}, "Peso (kg)"),
                    th({}, "Valor NF Padrão"),
                    th({}, "Ações")
                )
            ),
            tbody({},
                *[tr({},
                    td({}, p.nome),
                    td({}, f"{p.largura_cm} × {p.altura_cm} × {p.profundidade_cm}"),
                    td({}, f"{p.peso_real_kg}"),
                    td({}, f"R$ {p.valor_nf_padrao:.2f}"),
                    td({},
                        button({"class": "btn btn-sm btn-warning me-2",
                               "hx-get": f"/produtos/{p.id}/form", "hx-target": "#form-area"},
                            "Editar"
                        ),
                        button({"class": "btn btn-sm btn-danger",
                               "hx-delete": f"/produtos/{p.id}", "hx-target": "#produtos-table"},
                            "Excluir"
                        )
                    )
                ) for p in produtos]
            )
        )
    )

    return base_page("Produtos", content)


@router.get("/produtos/form", response_class=HTMLResponse)
def form_produto(session: Session = Depends(get_session)):
    """Formulário para novo produto"""
    return produto_form()


@router.get("/produtos/{produto_id}/form", response_class=HTMLResponse)
def form_editar_produto(produto_id: int, session: Session = Depends(get_session)):
    """Formulário para editar produto"""
    produto = session.get(Produto, produto_id)
    if not produto:
        return alert("Produto não encontrado", "error")

    return produto_form(produto)


@router.post("/produtos", response_class=HTMLResponse)
def criar_produto(
    nome: str = Form(...),
    largura_cm: float = Form(...),
    altura_cm: float = Form(...),
    profundidade_cm: float = Form(...),
    peso_real_kg: float = Form(...),
    valor_nf_padrao: float = Form(0.0),
    session: Session = Depends(get_session)
):
    """Criar novo produto"""
    produto = Produto(
        nome=nome,
        largura_cm=largura_cm,
        altura_cm=altura_cm,
        profundidade_cm=profundidade_cm,
        peso_real_kg=peso_real_kg,
        valor_nf_padrao=valor_nf_padrao
    )

    session.add(produto)
    session.commit()

    return div({"hx-get": "/produtos", "hx-target": "body", "hx-trigger": "load"},
        alert("Produto criado com sucesso!", "success")
    )


@router.get("/versoes", response_class=HTMLResponse)
def listar_versoes(session: Session = Depends(get_session)):
    """Lista versões de tabela"""
    versoes = session.exec(select(VersaoTabela).order_by(VersaoTabela.vigente_desde.desc())).all()

    content = container(
        h2({}, "Versões de Tabela"),
        div({"class": "mb-3"},
            form(htmx_form("/versoes/upload", method="post", target="#upload-result"),
                input_({"type": "file", "name": "arquivo", "accept": ".pdf", "required": True}),
                input_({"type": "text", "name": "descricao", "placeholder": "Descrição da versão"}),
                button({"type": "submit", "class": "btn btn-primary"}, "Upload PDF")
            )
        ),
        div({"id": "upload-result"}),
        table({"class": "table table-striped"},
            thead({},
                tr({},
                    th({}, "Descrição"),
                    th({}, "Data"),
                    th({}, "Status"),
                    th({}, "Arquivo"),
                    th({}, "Ações")
                )
            ),
            tbody({},
                *[tr({},
                    td({}, v.descricao),
                    td({}, v.vigente_desde.strftime("%d/%m/%Y %H:%M")),
                    td({}, "Ativa" if v.ativa else "Inativa"),
                    td({}, v.arquivo_pdf or "N/A"),
                    td({},
                        button({"class": "btn btn-sm btn-success" if not v.ativa else "btn btn-sm btn-secondary",
                               "hx-post": f"/versoes/{v.id}/ativar" if not v.ativa else "",
                               "hx-target": "#versoes-table"},
                            "Ativar" if not v.ativa else "Ativa"
                        )
                    )
                ) for v in versoes]
            )
        )
    )

    return base_page("Versões", content)


@router.post("/versoes/upload", response_class=HTMLResponse)
def upload_versao(
    arquivo: UploadFile = File(...),
    descricao: str = Form(""),
    session: Session = Depends(get_session)
):
    """Upload e processamento de PDF de tabela"""
    try:
        # Salvar arquivo
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        file_path = os.path.join(UPLOAD_DIR, arquivo.filename)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(arquivo.file, buffer)

        # Processar PDF
        tarifas, params = parse_pdf_tabela(file_path)

        if not tarifas:
            return alert("Não foi possível extrair tarifas do PDF", "warning")

        # Criar nova versão
        versao = VersaoTabela(
            descricao=descricao or f"Upload em {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            arquivo_pdf=file_path,
            ativa=False
        )
        session.add(versao)
        session.commit()
        session.refresh(versao)

        # Salvar parâmetros
        params_obj = ParametrosGerais(versao_id=versao.id, **params)
        session.add(params_obj)

        # Salvar tarifas
        for categoria, tarifa_data in tarifas.items():
            tarifa_obj = TarifaPeso(
                versao_id=versao.id,
                categoria=categoria,
                **tarifa_data
            )
            session.add(tarifa_obj)

        session.commit()

        return alert(f"Versão criada com sucesso! {len(tarifas)} categorias encontradas.", "success")

    except Exception as e:
        return alert(f"Erro no upload: {str(e)}", "error")


def nav_menu():
    """Menu de navegação"""
    return div({"class": "nav-menu mb-4"},
        nav_link("/", "Calculadora", True),
        nav_link("/produtos", "Produtos"),
        nav_link("/versoes", "Versões"),
        nav_link("/destinos", "Destinos")
    )


def produto_form(produto: Optional[Produto] = None):
    """Formulário de produto"""
    is_edit = produto is not None
    action = f"/produtos/{produto.id}" if is_edit else "/produtos"
    method = "put" if is_edit else "post"

    return card({},
        h4({}, "Editar Produto" if is_edit else "Novo Produto"),
        form(htmx_form(action, method, "#form-area"),
            form_group("Nome:", {
                "name": "nome", "value": produto.nome if produto else "", "required": True
            }),
            form_group("Largura (cm):", {
                "type": "number", "name": "largura_cm", "step": "0.1",
                "value": produto.largura_cm if produto else "", "required": True
            }),
            form_group("Altura (cm):", {
                "type": "number", "name": "altura_cm", "step": "0.1",
                "value": produto.altura_cm if produto else "", "required": True
            }),
            form_group("Profundidade (cm):", {
                "type": "number", "name": "profundidade_cm", "step": "0.1",
                "value": produto.profundidade_cm if produto else "", "required": True
            }),
            form_group("Peso Real (kg):", {
                "type": "number", "name": "peso_real_kg", "step": "0.1",
                "value": produto.peso_real_kg if produto else "", "required": True
            }),
            form_group("Valor NF Padrão:", {
                "type": "number", "name": "valor_nf_padrao", "step": "0.01",
                "value": produto.valor_nf_padrao if produto else "0.00"
            }),
            div({"class": "text-center"},
                button({"type": "submit", "class": "btn btn-success"}, "Salvar"),
                button({"type": "button", "class": "btn btn-secondary ms-2",
                       "onclick": "document.getElementById('form-area').innerHTML = ''"},
                    "Cancelar"
                )
            )
        )
    )


def base_page(page_title: str, content: str):
    """Layout base das páginas"""
    return html(
        head(
            meta({"charset": "utf-8"}),
            meta({"name": "viewport", "content": "width=device-width, initial-scale=1"}),
            title(f"{page_title} - Rodonaves"),
            link({"rel": "stylesheet", "href": "/static/styles.css"}),
            script({"src": "/static/htmx.min.js"})
        ),
        body({},
            container(
                nav_menu(),
                content
            )
        )
    )