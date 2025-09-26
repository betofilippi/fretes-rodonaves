from sqlmodel import Session, select
from .db import engine
from .models import Produto, VersaoTabela, ParametrosGerais, TarifaPeso, Destino


def seed_initial_data():
    """Popula dados iniciais se o banco estiver vazio"""
    with Session(engine) as session:
        # Verificar se já existem produtos
        existing_produtos = session.exec(select(Produto)).first()
        if existing_produtos:
            return  # Dados já existem

        # Criar produtos (móveis) - ESPECIFICAÇÕES CORRETAS DOCUMENTADAS
        produtos = [
            Produto(
                nome="Zilla",
                largura_cm=111.0,
                altura_cm=111.0,
                profundidade_cm=150.0,
                peso_real_kg=63.0,
                valor_nf_padrao=8100.00
            ),
            Produto(
                nome="Juna",
                largura_cm=78.0,
                altura_cm=186.0,
                profundidade_cm=128.0,
                peso_real_kg=123.0,
                valor_nf_padrao=15000.00
            ),
            Produto(
                nome="Kimbo",
                largura_cm=78.0,
                altura_cm=186.0,
                profundidade_cm=128.0,
                peso_real_kg=121.0,
                valor_nf_padrao=15000.00
            ),
            Produto(
                nome="Kay",
                largura_cm=78.0,
                altura_cm=186.0,
                profundidade_cm=128.0,
                peso_real_kg=161.0,
                valor_nf_padrao=16000.00
            ),
            Produto(
                nome="Jaya",
                largura_cm=78.0,
                altura_cm=186.0,
                profundidade_cm=128.0,
                peso_real_kg=107.0,
                valor_nf_padrao=14000.00
            )
        ]

        for produto in produtos:
            session.add(produto)

        # Criar alguns destinos exemplo
        destinos = [
            Destino(uf="SP", cidade="São Paulo", categoria="SP_CAPITAL"),
            Destino(uf="SP", cidade="Campinas", categoria="SP_INTERIOR_1"),
            Destino(uf="SP", cidade="Ribeirão Preto", categoria="SP_INTERIOR_2"),
            Destino(uf="RJ", cidade="Rio de Janeiro", categoria="RJ_CAPITAL"),
            Destino(uf="RJ", cidade="Niterói", categoria="RJ_METRO"),
            Destino(uf="MG", cidade="Belo Horizonte", categoria="MG_CAPITAL"),
            Destino(uf="MG", cidade="Uberlândia", categoria="MG_INTERIOR"),
            Destino(uf="PR", cidade="Curitiba", categoria="PR_CAPITAL"),
            Destino(uf="SC", cidade="Florianópolis", categoria="SC_CAPITAL"),
            Destino(uf="RS", cidade="Porto Alegre", categoria="RS_CAPITAL"),
        ]

        for destino in destinos:
            session.add(destino)

        # Criar versão padrão
        versao = VersaoTabela(
            descricao="Versão inicial - Dados de exemplo",
            ativa=True
        )
        session.add(versao)
        session.commit()
        session.refresh(versao)

        # Parâmetros gerais padrão
        params = ParametrosGerais(
            versao_id=versao.id,
            cubagem_kg_por_m3=300.0,
            fvalor_percent_padrao=0.005,
            fvalor_min=4.78,
            gris_percent_ate_10k=0.001,
            gris_percent_acima_10k=0.0023,
            gris_min=1.10,
            pedagio_por_100kg=3.80,
            icms_percent=0.12
        )
        session.add(params)

        # Tarifas exemplo (valores aproximados)
        tarifas_exemplo = [
            # SP Capital
            TarifaPeso(
                versao_id=versao.id,
                categoria="SP_CAPITAL",
                ate_10=25.00,
                ate_20=35.00,
                ate_40=55.00,
                ate_60=75.00,
                ate_100=120.00,
                excedente_por_kg=1.20
            ),
            # SP Interior 1
            TarifaPeso(
                versao_id=versao.id,
                categoria="SP_INTERIOR_1",
                ate_10=30.00,
                ate_20=42.00,
                ate_40=65.00,
                ate_60=88.00,
                ate_100=140.00,
                excedente_por_kg=1.40
            ),
            # SP Interior 2
            TarifaPeso(
                versao_id=versao.id,
                categoria="SP_INTERIOR_2",
                ate_10=35.00,
                ate_20=48.00,
                ate_40=75.00,
                ate_60=100.00,
                ate_100=160.00,
                excedente_por_kg=1.60
            ),
            # RJ Capital
            TarifaPeso(
                versao_id=versao.id,
                categoria="RJ_CAPITAL",
                ate_10=40.00,
                ate_20=55.00,
                ate_40=85.00,
                ate_60=115.00,
                ate_100=180.00,
                excedente_por_kg=1.80
            ),
            # RJ Metro
            TarifaPeso(
                versao_id=versao.id,
                categoria="RJ_METRO",
                ate_10=38.00,
                ate_20=52.00,
                ate_40=80.00,
                ate_60=108.00,
                ate_100=170.00,
                excedente_por_kg=1.70
            ),
            # MG Capital
            TarifaPeso(
                versao_id=versao.id,
                categoria="MG_CAPITAL",
                ate_10=45.00,
                ate_20=62.00,
                ate_40=95.00,
                ate_60=128.00,
                ate_100=200.00,
                excedente_por_kg=2.00
            ),
            # MG Interior
            TarifaPeso(
                versao_id=versao.id,
                categoria="MG_INTERIOR",
                ate_10=50.00,
                ate_20=68.00,
                ate_40=105.00,
                ate_60=140.00,
                ate_100=220.00,
                excedente_por_kg=2.20
            ),
            # PR Capital
            TarifaPeso(
                versao_id=versao.id,
                categoria="PR_CAPITAL",
                ate_10=55.00,
                ate_20=75.00,
                ate_40=115.00,
                ate_60=155.00,
                ate_100=240.00,
                excedente_por_kg=2.40
            ),
            # SC Capital
            TarifaPeso(
                versao_id=versao.id,
                categoria="SC_CAPITAL",
                ate_10=60.00,
                ate_20=82.00,
                ate_40=125.00,
                ate_60=168.00,
                ate_100=260.00,
                excedente_por_kg=2.60
            ),
            # RS Capital
            TarifaPeso(
                versao_id=versao.id,
                categoria="RS_CAPITAL",
                ate_10=65.00,
                ate_20=88.00,
                ate_40=135.00,
                ate_60=180.00,
                ate_100=280.00,
                excedente_por_kg=2.80
            ),
        ]

        for tarifa in tarifas_exemplo:
            session.add(tarifa)

        session.commit()

        print("Dados iniciais criados com sucesso!")
        print(f"- {len(produtos)} produtos")
        print(f"- {len(destinos)} destinos")
        print(f"- {len(tarifas_exemplo)} tarifas")
        print("- 1 versão padrão ativa")