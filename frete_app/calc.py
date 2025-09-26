from dataclasses import dataclass
from math import ceil
from typing import Optional

@dataclass
class CalcInput:
    largura_cm: float
    altura_cm: float
    profundidade_cm: float
    peso_real_kg: float
    valor_nf: float
    categoria_destino: str
    corredor_f: Optional[float] = None
    pedagio_pracas: Optional[int] = None
    fvalor_percent_override: Optional[float] = None

@dataclass
class ParamSet:
    cubagem_kg_por_m3: float
    fvalor_percent_padrao: float
    fvalor_min: float
    gris_percent_ate_10k: float
    gris_percent_acima_10k: float
    gris_min: float
    pedagio_por_100kg: float
    icms_percent: float

@dataclass
class Tarifa:
    ate_10: float
    ate_20: float
    ate_40: float
    ate_60: float
    ate_100: float
    excedente_por_kg: float

@dataclass
class CalcBreakdown:
    peso_cubado: float
    peso_taxavel: int
    base_faixa: float
    excedente_valor: float
    pedagio: float
    fvalor: float
    gris: float
    icms: float
    total: float


def cubagem_kg(l, a, p, dens):
    """Calcula peso cubado em kg baseado nas dimensões em cm"""
    m3 = (l/100) * (a/100) * (p/100)
    return m3 * dens


def base_por_peso(kg: int, tarifa: Tarifa) -> float:
    """Retorna valor base conforme faixa de peso"""
    if kg <= 10:
        return tarifa.ate_10
    elif kg <= 20:
        return tarifa.ate_20
    elif kg <= 40:
        return tarifa.ate_40
    elif kg <= 60:
        return tarifa.ate_60
    elif kg <= 100:
        return tarifa.ate_100
    else:
        return tarifa.ate_100 + (kg - 100) * tarifa.excedente_por_kg


def aplica_corredor_f(valor: float, f: Optional[float]) -> float:
    """Aplica fator multiplicador do corredor KM"""
    return round(valor * (f if f else 1.0), 2)


def calcula_frete(inp: CalcInput, tarifa: Tarifa, params: ParamSet) -> CalcBreakdown:
    """Motor principal de cálculo de frete"""
    # Peso cubado
    pc = cubagem_kg(inp.largura_cm, inp.altura_cm, inp.profundidade_cm, params.cubagem_kg_por_m3)

    # Peso taxável (maior entre real e cubado, arredondado para cima)
    kg = int(ceil(max(pc, inp.peso_real_kg)))

    # Valor base por faixa
    base = base_por_peso(kg, tarifa)
    base = aplica_corredor_f(base, inp.corredor_f)

    # Separar excedente para exibição detalhada
    if kg > 100:
        excedente_valor = aplica_corredor_f((kg - 100) * tarifa.excedente_por_kg, inp.corredor_f)
        base_faixa = aplica_corredor_f(tarifa.ate_100, inp.corredor_f)
    else:
        excedente_valor = 0.0
        base_faixa = base

    # Pedágio: Fixed rate based on real CTE data (R$ 6.46 regardless of weight)
    pedagio_unit = params.pedagio_por_100kg

    # Se corredor define nº de praças, usar isso ao invés
    if inp.pedagio_pracas is not None:
        pedagio_total = inp.pedagio_pracas * pedagio_unit
    else:
        # Use fixed pedagio amount (not weight-based) to match real CTE data
        pedagio_total = pedagio_unit

    # F-valor
    fvalor_pct = inp.fvalor_percent_override or params.fvalor_percent_padrao
    fvalor = max(inp.valor_nf * fvalor_pct, params.fvalor_min)

    # GRIS
    gris_pct = params.gris_percent_ate_10k if inp.valor_nf <= 10_000 else params.gris_percent_acima_10k
    gris = max(inp.valor_nf * gris_pct, params.gris_min)

    # Subtotal
    subtotal = base + pedagio_total + fvalor + gris

    # ICMS
    icms = round(subtotal * params.icms_percent, 2)
    total = round(subtotal + icms, 2)

    return CalcBreakdown(
        peso_cubado=round(pc, 2),
        peso_taxavel=kg,
        base_faixa=round(base_faixa, 2),
        excedente_valor=round(excedente_valor, 2),
        pedagio=round(pedagio_total, 2),
        fvalor=round(fvalor, 2),
        gris=round(gris, 2),
        icms=icms,
        total=total
    )