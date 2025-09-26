"""
Motor de cálculo estendido com suporte a TDAs e TRTs
Baseado no calc.py original, mas com suporte às taxas especiais
"""

from math import ceil
from typing import Optional, List
from dataclasses import dataclass
from sqlmodel import Session, select

try:
    from .db import engine
    from .models import Produto, VersaoTabela, ParametrosGerais, TarifaPeso
    from .models_extended import CidadeRodonaves, TaxaEspecial, TabelaTarifaCompleta
    from .calc import CalcInput, CalcBreakdown, Tarifa, ParamSet, calcula_frete, cubagem_kg
except ImportError:
    from db import engine
    from models import Produto, VersaoTabela, ParametrosGerais, TarifaPeso
    from models_extended import CidadeRodonaves, TaxaEspecial, TabelaTarifaCompleta
    from calc import CalcInput, CalcBreakdown, Tarifa, ParamSet, calcula_frete, cubagem_kg


@dataclass
class TaxasEspeciais:
    """Taxas especiais aplicáveis ao frete"""
    tem_tda: bool = False
    tem_trt: bool = False
    valor_tda: float = 0.0
    tipo_tda: str = "FIXO"  # FIXO ou PERCENTUAL
    valor_trt: float = 0.0
    tipo_trt: str = "FIXO"
    descricao: Optional[str] = None
    justificativa: Optional[str] = None


@dataclass
class CalcBreakdownExtended:
    """Breakdown estendido com taxas especiais"""
    # Campos do breakdown original
    peso_cubado: float
    peso_taxavel: int
    base_faixa: float
    excedente_valor: float
    pedagio: float
    fvalor: float
    gris: float
    icms: float
    total: float

    # Campos adicionais
    largura_cm: float = 0
    altura_cm: float = 0
    profundidade_cm: float = 0
    peso_real_kg: float = 0
    categoria: str = ""
    excedente_kg: float = 0

    # Taxas especiais
    tda: float = 0.0
    trt: float = 0.0
    tipo_tda: Optional[str] = None
    tipo_trt: Optional[str] = None
    justificativa_taxas: Optional[str] = None

    # Valores de embalagem e total final
    valor_embalagem: float = 0.0
    produto_nome: str = ""
    total_com_embalagem: float = 0.0

    # Prazos de entrega CPF
    prazo_cpf_min: Optional[int] = None
    prazo_cpf_max: Optional[int] = None
    prazo_formatado: Optional[str] = None
    tipo_transporte: Optional[str] = None

    def recalcular_total(self):
        """Recalcula o total incluindo TDA e TRT"""
        self.total = (
            self.base_faixa +
            self.excedente_valor +
            self.pedagio +
            self.fvalor +
            self.gris +
            self.icms +
            self.tda +
            self.trt
        )
        # Calcula total com embalagem
        self.total_com_embalagem = self.total + self.valor_embalagem


def buscar_taxas_especiais(cidade_id: int) -> TaxasEspeciais:
    """
    Busca taxas especiais (TDA/TRT) para uma cidade
    """
    with Session(engine) as session:
        # Buscar taxas da cidade
        taxas = session.exec(
            select(TaxaEspecial).where(
                TaxaEspecial.cidade_id == cidade_id,
                TaxaEspecial.valido_ate == None  # Apenas taxas ativas
            )
        ).all()

        if not taxas:
            return TaxasEspeciais()

        # Consolidar taxas (pode haver múltiplas entradas)
        resultado = TaxasEspeciais()

        for taxa in taxas:
            if taxa.valor_tda:
                resultado.tem_tda = True
                resultado.valor_tda = taxa.valor_tda
                resultado.tipo_tda = taxa.tipo_tda or "FIXO"

            if taxa.valor_trt:
                resultado.tem_trt = True
                resultado.valor_trt = taxa.valor_trt
                resultado.tipo_trt = taxa.tipo_trt or "FIXO"

            if taxa.descricao:
                resultado.descricao = taxa.descricao

            if taxa.justificativa:
                resultado.justificativa = taxa.justificativa

        return resultado


def aplicar_taxas_especiais(
    breakdown: CalcBreakdown,
    taxas: TaxasEspeciais,
    valor_nf: float,
    produto_info: dict = None
) -> CalcBreakdownExtended:
    """
    Aplica TDAs e TRTs ao cálculo base
    """
    # Converter para breakdown estendido
    extended = CalcBreakdownExtended(
        largura_cm=produto_info.get('largura_cm', 0) if produto_info else 0,
        altura_cm=produto_info.get('altura_cm', 0) if produto_info else 0,
        profundidade_cm=produto_info.get('profundidade_cm', 0) if produto_info else 0,
        peso_real_kg=produto_info.get('peso_real_kg', 0) if produto_info else 0,
        peso_cubado=breakdown.peso_cubado,
        peso_taxavel=breakdown.peso_taxavel,
        categoria=produto_info.get('categoria', '') if produto_info else '',
        base_faixa=breakdown.base_faixa,
        excedente_kg=0,  # Não está disponível no CalcBreakdown original
        excedente_valor=breakdown.excedente_valor,
        pedagio=breakdown.pedagio,
        fvalor=breakdown.fvalor,
        gris=breakdown.gris,
        icms=breakdown.icms,
        total=breakdown.total
    )

    # Calcular TDA
    if taxas.tem_tda:
        if taxas.tipo_tda == "PERCENTUAL":
            # TDA como percentual do valor da NF
            extended.tda = valor_nf * taxas.valor_tda
        else:
            # TDA como valor fixo
            extended.tda = taxas.valor_tda

        extended.tipo_tda = taxas.tipo_tda

    # Calcular TRT
    if taxas.tem_trt:
        if taxas.tipo_trt == "PERCENTUAL":
            # TRT como percentual do frete base (sem TDA)
            frete_base = extended.total
            extended.trt = frete_base * taxas.valor_trt
        else:
            # TRT como valor fixo
            extended.trt = taxas.valor_trt

        extended.tipo_trt = taxas.tipo_trt

    # Adicionar justificativa
    if taxas.justificativa:
        extended.justificativa_taxas = taxas.justificativa

    # Recalcular total
    extended.recalcular_total()

    return extended


def buscar_tarifa_cidade(cidade_id: int, versao_id: int) -> Optional[Tarifa]:
    """
    Busca a tarifa aplicável para uma cidade específica
    """
    with Session(engine) as session:
        # Buscar cidade
        cidade = session.get(CidadeRodonaves, cidade_id)
        if not cidade:
            return None

        # Buscar estado para categoria completa
        estado = cidade.estado
        categoria_completa = f"{estado.sigla}_{cidade.categoria_tarifa}"

        # Primeiro tentar tabela completa (nova)
        tarifa_completa = session.exec(
            select(TabelaTarifaCompleta).where(
                TabelaTarifaCompleta.versao_id == versao_id,
                TabelaTarifaCompleta.categoria_completa == categoria_completa
            )
        ).first()

        if tarifa_completa:
            return Tarifa(
                ate_10=tarifa_completa.ate_10,
                ate_20=tarifa_completa.ate_20,
                ate_40=tarifa_completa.ate_40,
                ate_60=tarifa_completa.ate_60,
                ate_100=tarifa_completa.ate_100,
                excedente_por_kg=tarifa_completa.excedente_por_kg
            )

        # Fallback para tabela antiga (compatibilidade)
        tarifa_peso = session.exec(
            select(TarifaPeso).where(
                TarifaPeso.versao_id == versao_id,
                TarifaPeso.categoria == categoria_completa
            )
        ).first()

        if tarifa_peso:
            return Tarifa(
                ate_10=tarifa_peso.ate_10,
                ate_20=tarifa_peso.ate_20,
                ate_40=tarifa_peso.ate_40,
                ate_60=tarifa_peso.ate_60,
                ate_100=tarifa_peso.ate_100,
                excedente_por_kg=tarifa_peso.excedente_por_kg
            )

        return None


def calcula_frete_completo(
    produto_id: int,
    cidade_id: int,
    valor_nf: Optional[float] = None,
    versao_id: Optional[int] = None
) -> Optional[CalcBreakdownExtended]:
    """
    Calcula frete completo com todas as taxas especiais
    """
    with Session(engine) as session:
        # Buscar produto
        produto = session.get(Produto, produto_id)
        if not produto:
            return None

        # Buscar cidade
        cidade = session.get(CidadeRodonaves, cidade_id)
        if not cidade:
            return None

        # Determinar versão a usar
        if not versao_id:
            versao = session.exec(
                select(VersaoTabela).where(VersaoTabela.ativa == True)
            ).first()
            if not versao:
                return None
            versao_id = versao.id

        # Buscar tarifa da cidade
        tarifa = buscar_tarifa_cidade(cidade_id, versao_id)
        if not tarifa:
            return None

        # Buscar parâmetros gerais
        params_db = session.exec(
            select(ParametrosGerais).where(
                ParametrosGerais.versao_id == versao_id
            )
        ).first()

        if not params_db:
            return None

        # Buscar tarifa completa para parâmetros regionais
        categoria_completa = f"{cidade.estado.sigla}_{cidade.categoria_tarifa}"
        tarifa_completa = session.exec(
            select(TabelaTarifaCompleta).where(
                TabelaTarifaCompleta.versao_id == versao_id,
                TabelaTarifaCompleta.categoria_completa == categoria_completa
            )
        ).first()

        # Usar parâmetros regionais se disponíveis, senão usar padrão
        if tarifa_completa and tarifa_completa.gris_percent_especial:
            # Estado com parâmetros especiais (use regional GRIS e ICMS)
            gris_percent_regional = tarifa_completa.gris_percent_especial
            icms_percent_regional = tarifa_completa.icms_percent or params_db.icms_percent
            fvalor_percent_regional = tarifa_completa.fvalor_percent_especial or params_db.fvalor_percent_padrao

            params = ParamSet(
                cubagem_kg_por_m3=params_db.cubagem_kg_por_m3,
                fvalor_percent_padrao=fvalor_percent_regional,
                fvalor_min=params_db.fvalor_min,
                gris_percent_ate_10k=gris_percent_regional,  # Use regional rate
                gris_percent_acima_10k=gris_percent_regional,  # Same rate for both brackets
                gris_min=params_db.gris_min,
                pedagio_por_100kg=params_db.pedagio_por_100kg,
                icms_percent=icms_percent_regional  # Use state-specific ICMS
            )
        else:
            # Use default parameters for states without special rates
            params = ParamSet(
                cubagem_kg_por_m3=params_db.cubagem_kg_por_m3,
                fvalor_percent_padrao=params_db.fvalor_percent_padrao,
                fvalor_min=params_db.fvalor_min,
                gris_percent_ate_10k=params_db.gris_percent_ate_10k,
                gris_percent_acima_10k=params_db.gris_percent_acima_10k,
                gris_min=params_db.gris_min,
                pedagio_por_100kg=params_db.pedagio_por_100kg,
                icms_percent=params_db.icms_percent
            )

        # Usar valor da NF do produto se não fornecido
        if valor_nf is None:
            valor_nf = produto.valor_nf_padrao

        # Criar input para cálculo
        categoria_completa = f"{cidade.estado.sigla}_{cidade.categoria_tarifa}"
        calc_input = CalcInput(
            largura_cm=produto.largura_cm,
            altura_cm=produto.altura_cm,
            profundidade_cm=produto.profundidade_cm,
            peso_real_kg=produto.peso_real_kg,
            valor_nf=valor_nf,
            categoria_destino=categoria_completa
        )

        # Calcular frete base
        breakdown_base = calcula_frete(calc_input, tarifa, params)

        # Buscar taxas especiais
        taxas = buscar_taxas_especiais(cidade_id)

        # Informações do produto para o breakdown
        produto_info = {
            'largura_cm': produto.largura_cm,
            'altura_cm': produto.altura_cm,
            'profundidade_cm': produto.profundidade_cm,
            'peso_real_kg': produto.peso_real_kg,
            'categoria': categoria_completa
        }

        # Aplicar taxas especiais
        breakdown_final = aplicar_taxas_especiais(
            breakdown_base, taxas, valor_nf, produto_info
        )

        # Adicionar informações da embalagem
        breakdown_final.produto_nome = produto.nome
        breakdown_final.valor_embalagem = produto.valor_nf_padrao  # Valor da embalagem do produto
        breakdown_final.total_com_embalagem = breakdown_final.total + breakdown_final.valor_embalagem

        # Adicionar prazos de entrega CPF
        if cidade.prazo_cpf_min_dias and cidade.prazo_cpf_max_dias:
            breakdown_final.prazo_cpf_min = cidade.prazo_cpf_min_dias
            breakdown_final.prazo_cpf_max = cidade.prazo_cpf_max_dias
            breakdown_final.prazo_formatado = f"{cidade.prazo_cpf_min_dias} a {cidade.prazo_cpf_max_dias} dias"
            breakdown_final.tipo_transporte = cidade.tipo_transporte or "RODOVIARIO"
        else:
            # Fallback para prazo antigo se não tiver CPF específico
            if cidade.prazo_entrega_dias:
                breakdown_final.prazo_cpf_min = cidade.prazo_entrega_dias
                breakdown_final.prazo_cpf_max = cidade.prazo_entrega_dias
                breakdown_final.prazo_formatado = f"{cidade.prazo_entrega_dias} dias"
                breakdown_final.tipo_transporte = "RODOVIARIO"

        return breakdown_final


def listar_cidades_com_taxas(uf: Optional[str] = None, limite: int = 100) -> List[dict]:
    """
    Lista cidades que possuem TDA ou TRT
    """
    with Session(engine) as session:
        query = select(CidadeRodonaves).where(
            (CidadeRodonaves.tem_tda == True) |
            (CidadeRodonaves.tem_trt == True)
        )

        if uf:
            query = query.join(CidadeRodonaves.estado).where(
                CidadeRodonaves.estado.has(sigla=uf)
            )

        query = query.limit(limite)
        cidades = session.exec(query).all()

        resultado = []
        for cidade in cidades:
            taxas = buscar_taxas_especiais(cidade.id)

            info = {
                'id': cidade.id,
                'nome': cidade.nome,
                'uf': cidade.estado.sigla,
                'categoria': cidade.categoria_tarifa,
                'tem_tda': cidade.tem_tda,
                'tem_trt': cidade.tem_trt
            }

            if taxas.tem_tda:
                info['tda_valor'] = taxas.valor_tda
                info['tda_tipo'] = taxas.tipo_tda

            if taxas.tem_trt:
                info['trt_valor'] = taxas.valor_trt
                info['trt_tipo'] = taxas.tipo_trt

            if taxas.justificativa:
                info['justificativa'] = taxas.justificativa

            resultado.append(info)

        return resultado


# Funções de exemplo e teste
def exemplo_calculo_com_taxas():
    """
    Exemplo de cálculo com taxas especiais
    """
    # IDs de exemplo (ajustar conforme banco)
    produto_id = 1  # Zilla
    cidade_id = 100  # Alguma cidade com TDA/TRT

    resultado = calcula_frete_completo(
        produto_id=produto_id,
        cidade_id=cidade_id,
        valor_nf=2000.00
    )

    if resultado:
        print("\n📦 CÁLCULO DE FRETE COMPLETO")
        print("="*40)
        print(f"Produto: {resultado.largura_cm}x{resultado.altura_cm}x{resultado.profundidade_cm}cm")
        print(f"Peso: {resultado.peso_real_kg}kg")
        print(f"Peso cubado: {resultado.peso_cubado}kg")
        print(f"Peso taxável: {resultado.peso_taxavel}kg")
        print(f"\n💰 COMPONENTES DO FRETE:")
        print(f"  Base (faixa): R$ {resultado.base_faixa:.2f}")
        if resultado.excedente_valor > 0:
            print(f"  Excedente: R$ {resultado.excedente_valor:.2f}")
        print(f"  Pedágio: R$ {resultado.pedagio:.2f}")
        print(f"  F-Valor: R$ {resultado.fvalor:.2f}")
        print(f"  GRIS: R$ {resultado.gris:.2f}")
        print(f"  ICMS: R$ {resultado.icms:.2f}")

        if resultado.tda > 0:
            tipo = "%" if resultado.tipo_tda == "PERCENTUAL" else "fixo"
            print(f"  TDA ({tipo}): R$ {resultado.tda:.2f}")

        if resultado.trt > 0:
            tipo = "%" if resultado.tipo_trt == "PERCENTUAL" else "fixo"
            print(f"  TRT ({tipo}): R$ {resultado.trt:.2f}")

        print(f"\n💵 TOTAL: R$ {resultado.total:.2f}")

        if resultado.justificativa_taxas:
            print(f"\n📝 Justificativa taxas: {resultado.justificativa_taxas}")
    else:
        print("❌ Não foi possível calcular o frete")


if __name__ == "__main__":
    # Testar funções
    print("🚀 Testando cálculo estendido com taxas especiais")

    # Listar algumas cidades com taxas
    print("\n📍 Cidades com TDA/TRT:")
    cidades = listar_cidades_com_taxas(limite=10)
    for cidade in cidades:
        print(f"  - {cidade['nome']}/{cidade['uf']}: ", end="")
        if cidade.get('tem_tda'):
            print(f"TDA ", end="")
        if cidade.get('tem_trt'):
            print(f"TRT ", end="")
        print()

    # Exemplo de cálculo
    exemplo_calculo_com_taxas()