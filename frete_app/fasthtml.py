from typing import Any, Dict, Union, List
from html import escape


def _attrs(attrs: Dict[str, Any]) -> str:
    """Converte dicionário de atributos para string HTML"""
    if not attrs:
        return ""
    parts = []
    for k, v in attrs.items():
        if v is None or v is False:
            continue
        if v is True:
            parts.append(k)
        else:
            escaped_value = escape(str(v), quote=True)
            parts.append(f'{k}="{escaped_value}"')
    return " " + " ".join(parts) if parts else ""


def _tag(name: str, attrs: Dict[str, Any] = None, *children, self_closing: bool = False):
    """Cria tag HTML genérica"""
    attrs = attrs or {}

    if self_closing:
        return f"<{name}{_attrs(attrs)}/>"

    inner = ""
    for child in children:
        if child is not None:
            inner += str(child)

    return f"<{name}{_attrs(attrs)}>{inner}</{name}>"


# Tags básicas de estrutura
def html(*children):
    return _tag("html", None, *children)


def head(*children):
    return _tag("head", None, *children)


def body(attrs: Dict[str, Any] = None, *children):
    return _tag("body", attrs, *children)


def div(attrs: Dict[str, Any] = None, *children):
    return _tag("div", attrs, *children)


def span(attrs: Dict[str, Any] = None, *children):
    return _tag("span", attrs, *children)


def p(attrs: Dict[str, Any] = None, *children):
    return _tag("p", attrs, *children)


def strong(attrs: Dict[str, Any] = None, *children):
    return _tag("strong", attrs, *children)


def h1(attrs: Dict[str, Any] = None, *children):
    return _tag("h1", attrs, *children)


def h2(attrs: Dict[str, Any] = None, *children):
    return _tag("h2", attrs, *children)


def h3(attrs: Dict[str, Any] = None, *children):
    return _tag("h3", attrs, *children)


def h4(attrs: Dict[str, Any] = None, *children):
    return _tag("h4", attrs, *children)


def h5(attrs: Dict[str, Any] = None, *children):
    return _tag("h5", attrs, *children)


# Tags de tabela
def table(attrs: Dict[str, Any] = None, *children):
    return _tag("table", attrs, *children)


def thead(attrs: Dict[str, Any] = None, *children):
    return _tag("thead", attrs, *children)


def tbody(attrs: Dict[str, Any] = None, *children):
    return _tag("tbody", attrs, *children)


def tr(attrs: Dict[str, Any] = None, *children):
    return _tag("tr", attrs, *children)


def th(attrs: Dict[str, Any] = None, *children):
    return _tag("th", attrs, *children)


def td(attrs: Dict[str, Any] = None, *children):
    return _tag("td", attrs, *children)


# Tags de formulário
def form(attrs: Dict[str, Any] = None, *children):
    return _tag("form", attrs, *children)


def input_(attrs: Dict[str, Any] = None):
    return _tag("input", attrs, self_closing=True)


def textarea(attrs: Dict[str, Any] = None, *children):
    return _tag("textarea", attrs, *children)


def select_(attrs: Dict[str, Any] = None, *options):
    return _tag("select", attrs, *options)


def option(attrs: Dict[str, Any] = None, *children):
    return _tag("option", attrs, *children)


def label(attrs: Dict[str, Any] = None, *children):
    return _tag("label", attrs, *children)


def button(attrs: Dict[str, Any] = None, *children):
    return _tag("button", attrs, *children)


# Tags de lista
def ul(attrs: Dict[str, Any] = None, *children):
    return _tag("ul", attrs, *children)


def ol(attrs: Dict[str, Any] = None, *children):
    return _tag("ol", attrs, *children)


def li(attrs: Dict[str, Any] = None, *children):
    return _tag("li", attrs, *children)


# Tags de link e imagem
def a(attrs: Dict[str, Any] = None, *children):
    return _tag("a", attrs, *children)


def img(attrs: Dict[str, Any] = None):
    return _tag("img", attrs, self_closing=True)


# Tags meta
def meta(attrs: Dict[str, Any] = None):
    return _tag("meta", attrs, self_closing=True)


def link(attrs: Dict[str, Any] = None):
    return _tag("link", attrs, self_closing=True)


def script(attrs: Dict[str, Any] = None, *children):
    return _tag("script", attrs, *children)


def style(attrs: Dict[str, Any] = None, *children):
    return _tag("style", attrs, *children)


def title(*children):
    return _tag("title", None, *children)


# Helpers específicos para HTMX
def hx_get(url: str, **kwargs):
    """Helper para hx-get"""
    attrs = {"hx-get": url, **kwargs}
    return attrs


def hx_post(url: str, **kwargs):
    """Helper para hx-post"""
    attrs = {"hx-post": url, **kwargs}
    return attrs


def hx_target(selector: str):
    """Helper para hx-target"""
    return {"hx-target": selector}


def hx_swap(method: str):
    """Helper para hx-swap"""
    return {"hx-swap": method}


# Componentes compostos úteis
def card(attrs: Dict[str, Any] = None, *children):
    """Componente de cartão"""
    attrs = attrs or {}
    classes = attrs.get("class", "") + " card"
    attrs["class"] = classes.strip()
    return div(attrs, *children)


def form_group(label_text: str, input_attrs: Dict[str, Any] = None, **kwargs):
    """Grupo de formulário com label e input"""
    input_attrs = input_attrs or {}
    input_id = input_attrs.get("id") or input_attrs.get("name", "")

    return div({"class": "form-group"},
        label({"for": input_id}, label_text),
        input_(input_attrs)
    )


def nav_link(href: str, text: str, active: bool = False):
    """Link de navegação"""
    classes = "nav-link"
    if active:
        classes += " active"

    return a({"href": href, "class": classes}, text)


def alert(message: str, type_: str = "info"):
    """Componente de alerta"""
    return div({"class": f"alert alert-{type_}"}, message)


def container(*children):
    """Container responsivo"""
    return div({"class": "container"}, *children)


def row(*children):
    """Linha do grid"""
    return div({"class": "row"}, *children)


def col(size: Union[str, int] = None, *children):
    """Coluna do grid"""
    classes = "col"
    if size:
        classes += f"-{size}"

    return div({"class": classes}, *children)


# Helpers para formulários HTMX
def htmx_form(action: str, method: str = "post", target: str = None, swap: str = "innerHTML", **kwargs):
    """Formulário HTMX configurado"""
    attrs = {}

    if method.lower() == "post":
        attrs["hx-post"] = action
    elif method.lower() == "get":
        attrs["hx-get"] = action

    if target:
        attrs["hx-target"] = target

    if swap:
        attrs["hx-swap"] = swap

    attrs.update(kwargs)
    return attrs


def loading_indicator():
    """Indicador de carregamento"""
    return div({"class": "htmx-indicator"}, "Carregando...")


# Componentes específicos da aplicação
def produto_select(produtos: List, selected_id: int = None):
    """Select de produtos"""
    options_list = [option({"value": ""}, "Selecione um produto")]

    for produto in produtos:
        attrs = {"value": produto.id}
        if selected_id == produto.id:
            attrs["selected"] = True
        options_list.append(
            option(attrs, f"{produto.nome} ({produto.largura_cm}x{produto.altura_cm}x{produto.profundidade_cm}cm)")
        )

    return select_({"name": "produto_id", "required": True}, *options_list)


def destino_select(destinos: List, selected_id: int = None):
    """Select de destinos"""
    options_list = [option({"value": ""}, "Selecione um destino")]

    for destino in destinos:
        attrs = {"value": destino.id}
        if selected_id == destino.id:
            attrs["selected"] = True
        options_list.append(
            option(attrs, f"{destino.cidade}/{destino.uf} ({destino.categoria})")
        )

    return select_({"name": "destino_id", "required": True}, *options_list)


def breakdown_table(breakdown):
    """Tabela de breakdown do cálculo"""
    return table({"class": "table table-breakdown"},
        tbody({},
            tr({}, th({}, "Peso cubado"), td({}, f"{breakdown.peso_cubado} kg")),
            tr({}, th({}, "Peso taxável"), td({}, f"{breakdown.peso_taxavel} kg")),
            tr({}, th({}, "Base (até 100kg)"), td({}, f"R$ {breakdown.base_faixa:.2f}")),
            tr({"class": "excedente" if breakdown.excedente_valor > 0 else "hidden"},
                th({}, "Excedente"),
                td({}, f"R$ {breakdown.excedente_valor:.2f}")
            ),
            tr({}, th({}, "Pedágio"), td({}, f"R$ {breakdown.pedagio:.2f}")),
            tr({}, th({}, "Frete-valor"), td({}, f"R$ {breakdown.fvalor:.2f}")),
            tr({}, th({}, "GRIS"), td({}, f"R$ {breakdown.gris:.2f}")),
            tr({}, th({}, "ICMS"), td({}, f"R$ {breakdown.icms:.2f}")),
            tr({"class": "total"}, th({}, "TOTAL"), td({}, f"R$ {breakdown.total:.2f}"))
        )
    )