#!/usr/bin/env python3
"""
Script para criar cidades de exemplo no banco de dados
"""

from sqlmodel import Session, select
from frete_app.db import engine, create_db_and_tables
from frete_app.models import VersaoTabela
from frete_app.models_extended import (
    Estado, FilialRodonaves, CidadeRodonaves,
    TaxaEspecial, TabelaTarifaCompleta
)
from datetime import datetime


def criar_dados_exemplo():
    """Cria dados de exemplo para testar o sistema"""

    create_db_and_tables()

    with Session(engine) as session:
        # Verificar se já existem dados
        if session.exec(select(CidadeRodonaves)).first():
            print("Ja existem cidades no banco")
            return

        print("Criando dados de exemplo...")

        # Criar estados
        estados_data = [
            ("SP", "Sao Paulo", "Sudeste"),
            ("RJ", "Rio de Janeiro", "Sudeste"),
            ("MG", "Minas Gerais", "Sudeste"),
            ("PR", "Parana", "Sul"),
            ("SC", "Santa Catarina", "Sul"),
            ("RS", "Rio Grande do Sul", "Sul"),
        ]

        estados = {}
        for sigla, nome, regiao in estados_data:
            estado = Estado(
                sigla=sigla,
                nome=nome,
                regiao=regiao,
                tem_cobertura=True
            )
            session.add(estado)
            session.commit()
            session.refresh(estado)
            estados[sigla] = estado

        # Criar filiais
        filiais_data = [
            ("SPO", "Sao Paulo", estados["SP"]),
            ("RJO", "Rio de Janeiro", estados["RJ"]),
            ("BHZ", "Belo Horizonte", estados["MG"]),
            ("CWB", "Curitiba", estados["PR"]),
            ("FLN", "Florianopolis", estados["SC"]),
            ("POA", "Porto Alegre", estados["RS"]),
        ]

        filiais = {}
        for codigo, nome, estado in filiais_data:
            filial = FilialRodonaves(
                codigo=codigo,
                nome=f"Filial {nome}",
                cidade=nome,
                estado_id=estado.id,
                tipo="FILIAL",
                ativa=True
            )
            session.add(filial)
            session.commit()
            session.refresh(filial)
            filiais[codigo] = filial

        # Criar cidades com diferentes categorias
        cidades_data = [
            # SP
            ("SAO PAULO", estados["SP"], filiais["SPO"], "CAPITAL", 0, 1, False, False),
            ("CAMPINAS", estados["SP"], filiais["SPO"], "INTERIOR_1", 100, 2, False, False),
            ("SANTOS", estados["SP"], filiais["SPO"], "INTERIOR_1", 80, 1, True, False),  # Com TDA
            ("RIBEIRAO PRETO", estados["SP"], filiais["SPO"], "INTERIOR_2", 320, 3, False, False),

            # RJ
            ("RIO DE JANEIRO", estados["RJ"], filiais["RJO"], "CAPITAL", 0, 1, False, True),  # Com TRT
            ("NITEROI", estados["RJ"], filiais["RJO"], "INTERIOR_1", 20, 1, False, False),
            ("CAMPOS", estados["RJ"], filiais["RJO"], "INTERIOR_2", 280, 3, True, True),  # Com TDA e TRT

            # MG
            ("BELO HORIZONTE", estados["MG"], filiais["BHZ"], "CAPITAL", 0, 1, False, False),
            ("UBERLANDIA", estados["MG"], filiais["BHZ"], "INTERIOR_1", 550, 2, False, False),
            ("JUIZ DE FORA", estados["MG"], filiais["BHZ"], "INTERIOR_2", 260, 2, True, False),  # Com TDA

            # PR
            ("CURITIBA", estados["PR"], filiais["CWB"], "CAPITAL", 0, 1, False, False),
            ("LONDRINA", estados["PR"], filiais["CWB"], "INTERIOR_1", 380, 2, False, False),
            ("FOZ DO IGUACU", estados["PR"], filiais["CWB"], "INTERIOR_2", 640, 3, True, False),  # Com TDA

            # SC
            ("FLORIANOPOLIS", estados["SC"], filiais["FLN"], "CAPITAL", 0, 1, False, False),
            ("JOINVILLE", estados["SC"], filiais["FLN"], "INTERIOR_1", 180, 2, False, False),

            # RS
            ("PORTO ALEGRE", estados["RS"], filiais["POA"], "CAPITAL", 0, 1, False, False),
            ("CAXIAS DO SUL", estados["RS"], filiais["POA"], "INTERIOR_1", 130, 2, False, True),  # Com TRT
        ]

        cidades = []
        for nome, estado, filial, categoria, distancia, prazo, tem_tda, tem_trt in cidades_data:
            cidade = CidadeRodonaves(
                nome=nome,
                estado_id=estado.id,
                filial_atendimento_id=filial.id,
                categoria_tarifa=categoria,
                distancia_km=distancia if distancia > 0 else None,
                prazo_entrega_dias=prazo,
                tem_tda=tem_tda,
                tem_trt=tem_trt,
                ativo=True
            )
            session.add(cidade)
            session.commit()
            session.refresh(cidade)
            cidades.append(cidade)

            # Criar taxas especiais se necessário
            if tem_tda or tem_trt:
                taxa = TaxaEspecial(
                    cidade_id=cidade.id,
                    tipo_taxa="AMBAS" if tem_tda and tem_trt else ("TDA" if tem_tda else "TRT"),
                    valor_tda=50.0 if tem_tda else None,  # R$ 50 fixo
                    tipo_tda="FIXO" if tem_tda else None,
                    valor_trt=30.0 if tem_trt else None,  # R$ 30 fixo
                    tipo_trt="FIXO" if tem_trt else None,
                    descricao=f"Taxa especial para {nome}",
                    justificativa="Zona de dificil acesso" if tem_tda else "Restricao municipal"
                )
                session.add(taxa)

        session.commit()

        # Criar tarifas para cada combinação estado/categoria
        versao = session.exec(select(VersaoTabela).where(VersaoTabela.ativa == True)).first()
        if versao:
            # Buscar combinações únicas
            combinacoes = set()
            for cidade in cidades:
                estado = session.get(Estado, cidade.estado_id)
                combinacoes.add((estado.sigla, cidade.categoria_tarifa))

            for uf, categoria in combinacoes:
                categoria_completa = f"{uf}_{categoria}"

                # Verificar se já existe
                if session.exec(
                    select(TabelaTarifaCompleta).where(
                        TabelaTarifaCompleta.categoria_completa == categoria_completa
                    )
                ).first():
                    continue

                # Base values
                base = 25.0
                if categoria == "INTERIOR_1":
                    base = 30.0
                elif categoria == "INTERIOR_2":
                    base = 35.0

                # Regional multiplier
                mult = 1.0
                if uf in ["RS", "SC"]:
                    mult = 2.5
                elif uf == "PR":
                    mult = 2.2
                elif uf == "MG":
                    mult = 1.8
                elif uf == "RJ":
                    mult = 1.6

                base = base * mult

                tarifa = TabelaTarifaCompleta(
                    versao_id=versao.id,
                    estado_sigla=uf,
                    categoria=categoria,
                    categoria_completa=categoria_completa,
                    ate_10=round(base, 2),
                    ate_20=round(base * 1.4, 2),
                    ate_40=round(base * 2.2, 2),
                    ate_60=round(base * 3.0, 2),
                    ate_100=round(base * 4.8, 2),
                    excedente_por_kg=round(base * 0.048, 2)
                )
                session.add(tarifa)

            session.commit()

        print(f"Criados:")
        print(f"  - {len(estados)} estados")
        print(f"  - {len(filiais)} filiais")
        print(f"  - {len(cidades)} cidades")
        print(f"  - {len([c for c in cidades if c.tem_tda])} cidades com TDA")
        print(f"  - {len([c for c in cidades if c.tem_trt])} cidades com TRT")
        print("Dados de exemplo criados com sucesso!")


if __name__ == "__main__":
    criar_dados_exemplo()