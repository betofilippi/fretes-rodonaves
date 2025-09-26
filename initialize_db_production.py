#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script robusto para inicializar o banco de dados em produção
Garante que todos os dados sejam carregados mesmo se alguns arquivos falharem
"""

import os
import sys
import logging
import traceback
from datetime import datetime
from pathlib import Path

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent))

def setup_logging():
    """Configura logging detalhado para debug no Railway"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S UTC'
    )
    return logging.getLogger(__name__)

def log_with_timestamp(logger, level, message):
    """Log com timestamp detalhado"""
    timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    log_message = f"[{timestamp}] {message}"
    getattr(logger, level)(log_message)
    print(log_message)  # Também imprimir para Railway logs

def init_production_database():
    """Inicializa o banco de dados com verificações robustas"""

    logger = setup_logging()
    log_with_timestamp(logger, 'info', "=== INICIANDO CONFIGURACAO DO BANCO DE DADOS PARA PRODUCAO ===")
    log_with_timestamp(logger, 'info', f"Python version: {sys.version}")
    log_with_timestamp(logger, 'info', f"Working directory: {os.getcwd()}")
    log_with_timestamp(logger, 'info', f"Script path: {__file__}")

    # Importar após adicionar ao path
    log_with_timestamp(logger, 'info', "Importando módulos do banco de dados...")
    try:
        from frete_app.db import create_db_and_tables, engine
        from sqlmodel import Session, select
        log_with_timestamp(logger, 'info', "Módulos do banco importados com sucesso")
    except Exception as e:
        log_with_timestamp(logger, 'error', f"ERRO ao importar módulos do banco: {e}")
        log_with_timestamp(logger, 'error', f"Traceback: {traceback.format_exc()}")
        return False

    # Criar tabelas
    log_with_timestamp(logger, 'info', "Criando tabelas do banco de dados...")
    try:
        start_time = datetime.utcnow()
        create_db_and_tables()
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        log_with_timestamp(logger, 'info', f"Tabelas criadas com sucesso em {duration:.2f} segundos")
    except Exception as e:
        log_with_timestamp(logger, 'error', f"ERRO CRITICO ao criar tabelas: {e}")
        log_with_timestamp(logger, 'error', f"Traceback completo: {traceback.format_exc()}")
        return False

    # 1. PRODUTOS - Dados essenciais hardcoded
    log_with_timestamp(logger, 'info', "=== ETAPA 1: VERIFICANDO E CRIANDO PRODUTOS ===")
    try:
        from frete_app.models import Produto
        log_with_timestamp(logger, 'info', "Modelo Produto importado com sucesso")
    except Exception as e:
        log_with_timestamp(logger, 'error', f"ERRO ao importar modelo Produto: {e}")
        return False

    try:
        with Session(engine) as session:
            log_with_timestamp(logger, 'info', "Conectado ao banco, verificando produtos existentes...")
            existing = session.exec(select(Produto)).first()

            if not existing:
                log_with_timestamp(logger, 'info', "Nenhum produto encontrado, criando produtos padrão...")
                produtos = [
                    Produto(nome="Juna", largura_cm=78.0, altura_cm=186.0,
                           profundidade_cm=128.0, peso_real_kg=123.0, valor_nf_padrao=2500.00),
                    Produto(nome="Kimbo", largura_cm=78.0, altura_cm=186.0,
                           profundidade_cm=128.0, peso_real_kg=121.0, valor_nf_padrao=2500.00),
                    Produto(nome="Kay", largura_cm=78.0, altura_cm=186.0,
                           profundidade_cm=128.0, peso_real_kg=161.0, valor_nf_padrao=3000.00),
                    Produto(nome="Jaya", largura_cm=78.0, altura_cm=186.0,
                           profundidade_cm=128.0, peso_real_kg=107.0, valor_nf_padrao=2200.00),
                ]

                for i, p in enumerate(produtos, 1):
                    log_with_timestamp(logger, 'info', f"Criando produto {i}/{len(produtos)}: {p.nome}")
                    session.add(p)

                start_commit = datetime.utcnow()
                session.commit()
                end_commit = datetime.utcnow()
                commit_duration = (end_commit - start_commit).total_seconds()

                log_with_timestamp(logger, 'info', f"SUCESSO: {len(produtos)} produtos criados em {commit_duration:.2f}s")
            else:
                # Contar produtos existentes
                total_produtos = len(session.exec(select(Produto)).all())
                log_with_timestamp(logger, 'info', f"Produtos já existem no banco: {total_produtos} produtos encontrados")
    except Exception as e:
        log_with_timestamp(logger, 'error', f"ERRO CRITICO na criação de produtos: {e}")
        log_with_timestamp(logger, 'error', f"Traceback: {traceback.format_exc()}")
        return False

    # 2. ESTADOS - Dados essenciais hardcoded
    log_with_timestamp(logger, 'info', "=== ETAPA 2: VERIFICANDO E CRIANDO ESTADOS ===")
    try:
        from frete_app.models_extended import Estado
        log_with_timestamp(logger, 'info', "Modelo Estado importado com sucesso")
    except Exception as e:
        log_with_timestamp(logger, 'error', f"ERRO ao importar modelo Estado: {e}")
        return False

    try:
        with Session(engine) as session:
            log_with_timestamp(logger, 'info', "Verificando estados existentes no banco...")
            existing = session.exec(select(Estado)).first()

            if not existing:
                log_with_timestamp(logger, 'info', "Nenhum estado encontrado, criando todos os 27 estados brasileiros...")
                estados_brasil = [
                    ("AC", "Acre", "Norte"), ("AL", "Alagoas", "Nordeste"), ("AP", "Amapá", "Norte"), ("AM", "Amazonas", "Norte"),
                    ("BA", "Bahia", "Nordeste"), ("CE", "Ceará", "Nordeste"), ("DF", "Distrito Federal", "Centro-Oeste"),
                    ("ES", "Espírito Santo", "Sudeste"), ("GO", "Goiás", "Centro-Oeste"), ("MA", "Maranhão", "Nordeste"),
                    ("MT", "Mato Grosso", "Centro-Oeste"), ("MS", "Mato Grosso do Sul", "Centro-Oeste"),
                    ("MG", "Minas Gerais", "Sudeste"), ("PA", "Pará", "Norte"), ("PB", "Paraíba", "Nordeste"),
                    ("PR", "Paraná", "Sul"), ("PE", "Pernambuco", "Nordeste"), ("PI", "Piauí", "Nordeste"),
                    ("RJ", "Rio de Janeiro", "Sudeste"), ("RN", "Rio Grande do Norte", "Nordeste"),
                    ("RS", "Rio Grande do Sul", "Sul"), ("RO", "Rondônia", "Norte"), ("RR", "Roraima", "Norte"),
                    ("SC", "Santa Catarina", "Sul"), ("SP", "São Paulo", "Sudeste"), ("SE", "Sergipe", "Nordeste"),
                    ("TO", "Tocantins", "Norte")
                ]

                log_with_timestamp(logger, 'info', f"Iniciando criação de {len(estados_brasil)} estados...")
                for i, (uf, nome, regiao) in enumerate(estados_brasil, 1):
                    estado = Estado(sigla=uf, nome=nome, regiao=regiao)
                    session.add(estado)
                    if i % 10 == 0:
                        log_with_timestamp(logger, 'info', f"Criados {i}/{len(estados_brasil)} estados...")

                start_commit = datetime.utcnow()
                session.commit()
                end_commit = datetime.utcnow()
                commit_duration = (end_commit - start_commit).total_seconds()

                log_with_timestamp(logger, 'info', f"SUCESSO: {len(estados_brasil)} estados criados em {commit_duration:.2f}s")
            else:
                # Contar estados existentes
                total_estados = len(session.exec(select(Estado)).all())
                log_with_timestamp(logger, 'info', f"Estados já existem no banco: {total_estados} estados encontrados")
    except Exception as e:
        log_with_timestamp(logger, 'error', f"ERRO CRITICO na criação de estados: {e}")
        log_with_timestamp(logger, 'error', f"Traceback: {traceback.format_exc()}")
        return False

    # 3. FILIAIS E CIDADES - Tentar importar dos Excel ou usar fallback
    log_with_timestamp(logger, 'info', "=== ETAPA 3: VERIFICANDO E IMPORTANDO CIDADES ===")
    try:
        from frete_app.models_extended import CidadeRodonaves, FilialRodonaves
        log_with_timestamp(logger, 'info', "Modelos de Cidade e Filial importados com sucesso")
    except Exception as e:
        log_with_timestamp(logger, 'error', f"ERRO ao importar modelos de Cidade/Filial: {e}")
        return False

    try:
        with Session(engine) as session:
            log_with_timestamp(logger, 'info', "Verificando cidades existentes no banco...")
            cidade_count = session.exec(select(CidadeRodonaves)).first()

            if not cidade_count:
                log_with_timestamp(logger, 'info', "Nenhuma cidade encontrada, iniciando importação...")

                # Usar o novo script de importação que tem fallback embutido
                try:
                    log_with_timestamp(logger, 'info', "Tentando importar módulo de cidades...")
                    from import_cities_data import import_cities_from_excel, create_essential_cities
                    log_with_timestamp(logger, 'info', "Módulo de cidades importado com sucesso")

                    # Tentar importar do Excel
                    log_with_timestamp(logger, 'info', "Iniciando importação de cidades do Excel...")
                    start_import = datetime.utcnow()

                    if not import_cities_from_excel():
                        log_with_timestamp(logger, 'warning', "Importação do Excel falhou, criando cidades essenciais...")
                        # Se falhar, criar cidades essenciais
                        create_essential_cities()
                        end_import = datetime.utcnow()
                        import_duration = (end_import - start_import).total_seconds()
                        log_with_timestamp(logger, 'info', f"Cidades essenciais criadas em {import_duration:.2f}s")
                    else:
                        end_import = datetime.utcnow()
                        import_duration = (end_import - start_import).total_seconds()
                        log_with_timestamp(logger, 'info', f"Cidades importadas do Excel em {import_duration:.2f}s")

                except Exception as e:
                    log_with_timestamp(logger, 'error', f"ERRO na importação de cidades: {e}")
                    log_with_timestamp(logger, 'error', f"Traceback: {traceback.format_exc()}")
                    # Fallback final - criar cidades mínimas
                    try:
                        log_with_timestamp(logger, 'info', "Tentando fallback final: criação de cidades mínimas...")
                        criar_cidades_minimas(session, logger)
                        log_with_timestamp(logger, 'info', "Cidades mínimas criadas como fallback final")
                    except Exception as e2:
                        log_with_timestamp(logger, 'error', f"ERRO CRITICO: Falha total ao criar cidades: {e2}")
                        log_with_timestamp(logger, 'error', f"Traceback fallback: {traceback.format_exc()}")
            else:
                # Contar cidades existentes
                total_cidades = len(session.exec(select(CidadeRodonaves)).all())
                total_filiais = len(session.exec(select(FilialRodonaves)).all())
                log_with_timestamp(logger, 'info', f"Cidades já existem no banco: {total_cidades} cidades, {total_filiais} filiais")
    except Exception as e:
        log_with_timestamp(logger, 'error', f"ERRO CRITICO na verificação de cidades: {e}")
        log_with_timestamp(logger, 'error', f"Traceback: {traceback.format_exc()}")
        return False

    # 4. Verificação final
    log_with_timestamp(logger, 'info', "=== ETAPA 4: VERIFICACAO FINAL E CONTAGEM DE REGISTROS ===")
    try:
        with Session(engine) as session:
            log_with_timestamp(logger, 'info', "Importando modelos para verificação final...")
            from frete_app.models import Produto, VersaoTabela, ParametrosGerais
            from frete_app.models_extended import Estado, FilialRodonaves, CidadeRodonaves

            log_with_timestamp(logger, 'info', "Contando registros em todas as tabelas...")

            start_count = datetime.utcnow()
            produtos = len(session.exec(select(Produto)).all())
            estados = len(session.exec(select(Estado)).all())
            filiais = len(session.exec(select(FilialRodonaves)).all())
            cidades = len(session.exec(select(CidadeRodonaves)).all())
            end_count = datetime.utcnow()
            count_duration = (end_count - start_count).total_seconds()

            log_with_timestamp(logger, 'info', f"Contagem finalizada em {count_duration:.2f}s")
            log_with_timestamp(logger, 'info', f"=== RESUMO FINAL DOS REGISTROS ===")
            log_with_timestamp(logger, 'info', f"Produtos cadastrados: {produtos}")
            log_with_timestamp(logger, 'info', f"Estados cadastrados: {estados}")
            log_with_timestamp(logger, 'info', f"Filiais cadastradas: {filiais}")
            log_with_timestamp(logger, 'info', f"Cidades cadastradas: {cidades}")

            # Verificar dados críticos
            critical_data_ok = True
            if produtos == 0:
                log_with_timestamp(logger, 'error', "ERRO CRITICO: Nenhum produto cadastrado!")
                critical_data_ok = False
            if estados == 0:
                log_with_timestamp(logger, 'error', "ERRO CRITICO: Nenhum estado cadastrado!")
                critical_data_ok = False

            # Avisos para dados opcionais
            if filiais == 0:
                log_with_timestamp(logger, 'warning', "AVISO: Nenhuma filial cadastrada")
            if cidades == 0:
                log_with_timestamp(logger, 'warning', "AVISO: Nenhuma cidade cadastrada")

            if critical_data_ok:
                log_with_timestamp(logger, 'info', "=== BANCO INICIALIZADO COM SUCESSO! ===")
                log_with_timestamp(logger, 'info', f"Total de registros criados: {produtos + estados + filiais + cidades}")
                return True
            else:
                log_with_timestamp(logger, 'error', "=== FALHA NA INICIALIZACAO: DADOS CRITICOS AUSENTES ===")
                return False

    except Exception as e:
        log_with_timestamp(logger, 'error', f"ERRO CRITICO na verificação final: {e}")
        log_with_timestamp(logger, 'error', f"Traceback: {traceback.format_exc()}")
        return False

def criar_cidades_minimas(session, logger):
    """Cria conjunto mínimo de cidades para funcionamento básico"""
    from frete_app.models_extended import FilialRodonaves, CidadeRodonaves, Estado
    from sqlmodel import select

    log_with_timestamp(logger, 'info', "=== CRIANDO CONJUNTO MINIMO DE CIDADES (FALLBACK) ===")

    # Buscar estados existentes
    log_with_timestamp(logger, 'info', "Buscando estados existentes para criação de cidades...")
    try:
        estados_list = session.exec(select(Estado)).all()
        estados = {estado.sigla: estado for estado in estados_list}
        log_with_timestamp(logger, 'info', f"Encontrados {len(estados)} estados para vincular cidades")
    except Exception as e:
        log_with_timestamp(logger, 'error', f"ERRO ao buscar estados: {e}")
        raise

    # Criar filial padrão para SP
    log_with_timestamp(logger, 'info', "Criando filial padrão em São Paulo...")
    estado_sp = estados.get("SP")
    if not estado_sp:
        log_with_timestamp(logger, 'error', "ERRO CRITICO: Estado SP não encontrado para criar filial")
        raise Exception("Estado SP não encontrado")

    try:
        filial = FilialRodonaves(
            codigo="SPO",
            nome="SAO PAULO",
            cidade="SAO PAULO",
            estado_id=estado_sp.id,
            tipo="MATRIZ",
            ativa=True
        )
        session.add(filial)
        session.commit()
        session.refresh(filial)
        log_with_timestamp(logger, 'info', f"Filial padrão criada: {filial.nome} (ID: {filial.id})")
    except Exception as e:
        log_with_timestamp(logger, 'error', f"ERRO ao criar filial padrão: {e}")
        raise

    # Criar cidades principais
    log_with_timestamp(logger, 'info', "Criando cidades principais do Brasil...")
    cidades_principais = [
        ("SP", "SAO PAULO", "CAPITAL", 4, 6),
        ("SP", "CAMPINAS", "INTERIOR_1", 5, 7),
        ("RJ", "RIO DE JANEIRO", "CAPITAL", 6, 8),
        ("MG", "BELO HORIZONTE", "CAPITAL", 7, 9),
        ("PR", "CURITIBA", "CAPITAL", 8, 10),
        ("RS", "PORTO ALEGRE", "CAPITAL", 9, 11),
        ("BA", "SALVADOR", "CAPITAL", 10, 12),
        ("PE", "RECIFE", "CAPITAL", 11, 13),
        ("CE", "FORTALEZA", "CAPITAL", 12, 14),
        ("DF", "BRASILIA", "CAPITAL", 8, 10),
    ]

    cidades_criadas = 0
    for i, (uf, nome_cidade, categoria, prazo_min, prazo_max) in enumerate(cidades_principais, 1):
        estado = estados.get(uf)
        if not estado:
            log_with_timestamp(logger, 'warning', f"Estado {uf} não encontrado para cidade {nome_cidade}")
            continue

        try:
            cidade_obj = CidadeRodonaves(
                nome=nome_cidade,
                estado_id=estado.id,
                filial_atendimento_id=filial.id,
                categoria_tarifa=categoria,
                prazo_cpf_min_dias=prazo_min,
                prazo_cpf_max_dias=prazo_max,
                tipo_transporte="RODOVIARIO",
                ativo=True
            )
            session.add(cidade_obj)
            cidades_criadas += 1
            log_with_timestamp(logger, 'info', f"Cidade {i}/{len(cidades_principais)}: {nome_cidade}/{uf} criada")
        except Exception as e:
            log_with_timestamp(logger, 'error', f"ERRO ao criar cidade {nome_cidade}/{uf}: {e}")

    try:
        start_commit = datetime.utcnow()
        session.commit()
        end_commit = datetime.utcnow()
        commit_duration = (end_commit - start_commit).total_seconds()
        log_with_timestamp(logger, 'info', f"SUCESSO: {cidades_criadas} cidades principais criadas em {commit_duration:.2f}s")
    except Exception as e:
        log_with_timestamp(logger, 'error', f"ERRO ao fazer commit das cidades: {e}")
        raise

if __name__ == "__main__":
    logger = setup_logging()

    try:
        import time
        log_with_timestamp(logger, 'info', "=== INICIANDO SCRIPT DE INICIALIZACAO PARA PRODUCAO ===")
        log_with_timestamp(logger, 'info', f"Timestamp de início: {datetime.utcnow().isoformat()}")

        # Pequena pausa para garantir que serviços estejam prontos
        log_with_timestamp(logger, 'info', "Aguardando 1 segundo para estabilização dos serviços...")
        time.sleep(1)

        start_time = datetime.utcnow()
        success = init_production_database()
        end_time = datetime.utcnow()
        total_duration = (end_time - start_time).total_seconds()

        if success:
            log_with_timestamp(logger, 'info', f"=== INICIALIZACAO CONCLUIDA COM SUCESSO EM {total_duration:.2f}s ===")
            log_with_timestamp(logger, 'info', f"Timestamp de conclusão: {end_time.isoformat()}")
            sys.exit(0)
        else:
            log_with_timestamp(logger, 'error', f"=== INICIALIZACAO FALHOU APOS {total_duration:.2f}s ===")
            log_with_timestamp(logger, 'error', f"Timestamp de falha: {end_time.isoformat()}")
            sys.exit(1)
    except Exception as e:
        log_with_timestamp(logger, 'error', f"=== ERRO FATAL DURANTE INICIALIZACAO ===")
        log_with_timestamp(logger, 'error', f"Erro: {e}")
        log_with_timestamp(logger, 'error', f"Traceback completo: {traceback.format_exc()}")
        log_with_timestamp(logger, 'error', f"Timestamp de erro fatal: {datetime.utcnow().isoformat()}")
        sys.exit(1)