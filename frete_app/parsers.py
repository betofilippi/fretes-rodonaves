from typing import Tuple, Dict, List
import pdfplumber
import camelot
import re
from pathlib import Path


def parse_pdf_tabela(path_pdf: str) -> Tuple[Dict[str, dict], dict]:
    """
    Extrai tarifas e parâmetros gerais de um PDF da Rodonaves

    Returns:
        Tuple[dict, dict]: (tarifas_por_categoria, parametros_gerais)
    """
    tarifas: Dict[str, dict] = {}
    params = {
        "cubagem_kg_por_m3": 300.0,
        "fvalor_percent_padrao": 0.005,
        "fvalor_min": 4.78,
        "gris_percent_ate_10k": 0.001,
        "gris_percent_acima_10k": 0.0023,
        "gris_min": 1.10,
        "pedagio_por_100kg": 3.80,
        "icms_percent": 0.12,
    }

    try:
        # 1) Extrair tabelas com Camelot
        tables = camelot.read_pdf(path_pdf, pages="1-end", flavor="lattice")

        for table in tables:
            df = table.df
            # Procurar tabelas com estrutura de faixas de peso
            if _is_tarifa_table(df):
                categoria = _extract_categoria_from_table(df)
                if categoria:
                    tarifa_data = _extract_tarifa_data(df)
                    if tarifa_data:
                        tarifas[categoria] = tarifa_data

        # 2) Extrair parâmetros gerais do texto
        with pdfplumber.open(path_pdf) as pdf:
            full_text = ""
            for page in pdf.pages:
                text = page.extract_text() or ""
                full_text += text + "\n"

            # Buscar padrões específicos nos textos
            params.update(_extract_params_from_text(full_text))

    except Exception as e:
        print(f"Erro ao processar PDF {path_pdf}: {e}")

    return tarifas, params


def _is_tarifa_table(df) -> bool:
    """Verifica se uma tabela contém estrutura de tarifas por peso"""
    if df.empty or len(df.columns) < 6:
        return False

    # Procurar por padrões como "0-10", "10-20", etc. nas células
    text_content = df.to_string().lower()
    peso_patterns = ["0-10", "10-20", "20-40", "40-60", "60-100", "excedente"]

    found_patterns = sum(1 for pattern in peso_patterns if pattern in text_content)
    return found_patterns >= 3  # Pelo menos 3 faixas encontradas


def _extract_categoria_from_table(df) -> str:
    """Extrai a categoria/destino da tabela"""
    # Procurar nas primeiras células por nomes de categorias
    for i in range(min(3, len(df))):
        for j in range(min(3, len(df.columns))):
            cell = str(df.iloc[i, j]).strip().upper()
            if any(uf in cell for uf in ["SP", "RJ", "MG", "PR", "SC", "RS"]):
                # Limpar e retornar categoria encontrada
                return _clean_categoria(cell)

    return f"CATEGORIA_{len(df)}"  # Fallback


def _clean_categoria(categoria: str) -> str:
    """Limpa e padroniza nome da categoria"""
    categoria = categoria.replace("\n", " ").strip()
    # Remover caracteres especiais, manter apenas letras, números e underscore
    categoria = re.sub(r'[^A-Za-z0-9_\s]', '', categoria)
    categoria = re.sub(r'\s+', '_', categoria)
    return categoria.upper()


def _extract_tarifa_data(df) -> Dict[str, float]:
    """Extrai os valores das faixas de tarifa da tabela"""
    tarifa = {
        "ate_10": 0.0,
        "ate_20": 0.0,
        "ate_40": 0.0,
        "ate_60": 0.0,
        "ate_100": 0.0,
        "excedente_por_kg": 0.0
    }

    # Percorrer todas as células procurando por valores monetários
    for i in range(len(df)):
        for j in range(len(df.columns)):
            cell = str(df.iloc[i, j]).strip()

            # Tentar extrair valor monetário da célula
            valor = _extract_monetary_value(cell)
            if valor > 0:
                # Determinar a qual faixa este valor pertence baseado no contexto
                context = _get_cell_context(df, i, j)
                faixa = _determine_faixa_from_context(context)
                if faixa and tarifa[faixa] == 0.0:  # Só atualizar se ainda não foi preenchido
                    tarifa[faixa] = valor

    return tarifa if any(v > 0 for v in tarifa.values()) else None


def _extract_monetary_value(cell: str) -> float:
    """Extrai valor monetário de uma célula de texto"""
    # Padrões para valores monetários brasileiros
    patterns = [
        r'R\$?\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)',  # R$ 1.234,56
        r'(\d{1,3}(?:\.\d{3})*(?:,\d{2}))',  # 1.234,56
        r'(\d+,\d{2})',  # 123,45
        r'(\d+\.\d{2})',  # 123.45 (formato internacional)
    ]

    for pattern in patterns:
        match = re.search(pattern, cell)
        if match:
            value_str = match.group(1)
            # Converter formato brasileiro para float
            value_str = value_str.replace('.', '').replace(',', '.')
            try:
                return float(value_str)
            except ValueError:
                continue

    return 0.0


def _get_cell_context(df, row: int, col: int) -> str:
    """Obtém contexto ao redor de uma célula para determinar a faixa"""
    context = ""

    # Verificar células adjacentes
    for r in range(max(0, row-1), min(len(df), row+2)):
        for c in range(max(0, col-1), min(len(df.columns), col+2)):
            context += " " + str(df.iloc[r, c])

    return context.lower()


def _determine_faixa_from_context(context: str) -> str:
    """Determina a faixa de peso baseado no contexto ao redor"""
    if any(pattern in context for pattern in ["0-10", "até 10", "ate 10"]):
        return "ate_10"
    elif any(pattern in context for pattern in ["10-20", "até 20", "ate 20"]):
        return "ate_20"
    elif any(pattern in context for pattern in ["20-40", "até 40", "ate 40"]):
        return "ate_40"
    elif any(pattern in context for pattern in ["40-60", "até 60", "ate 60"]):
        return "ate_60"
    elif any(pattern in context for pattern in ["60-100", "até 100", "ate 100"]):
        return "ate_100"
    elif any(pattern in context for pattern in ["excedente", "excesso", "adicional"]):
        return "excedente_por_kg"

    return None


def _extract_params_from_text(text: str) -> Dict[str, float]:
    """Extrai parâmetros gerais do texto do PDF"""
    params = {}

    # Padrões para diferentes parâmetros
    patterns = {
        "fvalor_percent_padrao": [
            r'frete.?valor[:\s]+(\d+,?\d*)%',
            r'f.?valor[:\s]+(\d+,?\d*)%'
        ],
        "fvalor_min": [
            r'frete.?valor.{0,20}mínimo[:\s]+r?\$?\s*(\d+,?\d*)',
            r'valor mínimo[:\s]+r?\$?\s*(\d+,?\d*)'
        ],
        "gris_percent_ate_10k": [
            r'gris.{0,30}até.{0,10}10\.?000[:\s]+(\d+,?\d*)%'
        ],
        "gris_percent_acima_10k": [
            r'gris.{0,30}acima.{0,10}10\.?000[:\s]+(\d+,?\d*)%'
        ],
        "pedagio_por_100kg": [
            r'pedágio[:\s]+r?\$?\s*(\d+,?\d*)',
            r'pedagio[:\s]+r?\$?\s*(\d+,?\d*)'
        ],
        "icms_percent": [
            r'icms[:\s]+(\d+,?\d*)%'
        ]
    }

    text_lower = text.lower()

    for param_name, regex_list in patterns.items():
        for pattern in regex_list:
            match = re.search(pattern, text_lower)
            if match:
                try:
                    value_str = match.group(1).replace(',', '.')
                    value = float(value_str)

                    # Converter percentuais para decimal se necessário
                    if 'percent' in param_name and value > 1:
                        value = value / 100

                    params[param_name] = value
                    break
                except ValueError:
                    continue

    return params


def extract_corredor_data_from_cte(path_pdf: str) -> Dict[str, any]:
    """
    Extrai dados de corredor KM de um CT-e

    Returns:
        Dict com: codigo, km, fator_multiplicador, etc.
    """
    corredor_data = {}

    try:
        with pdfplumber.open(path_pdf) as pdf:
            full_text = ""
            for page in pdf.pages:
                text = page.extract_text() or ""
                full_text += text + "\n"

            # Padrões específicos para CT-e
            patterns = {
                "codigo": r'corredor[:\s]+(\d+)',
                "km": r'distância[:\s]+(\d+(?:,\d+)?)\s*km',
                "fator_multiplicador": r'fator[:\s]+(\d+,?\d*)'
            }

            text_lower = full_text.lower()

            for key, pattern in patterns.items():
                match = re.search(pattern, text_lower)
                if match:
                    value = match.group(1).replace(',', '.')
                    try:
                        corredor_data[key] = float(value) if '.' in value else value
                    except ValueError:
                        corredor_data[key] = value

    except Exception as e:
        print(f"Erro ao processar CT-e {path_pdf}: {e}")

    return corredor_data