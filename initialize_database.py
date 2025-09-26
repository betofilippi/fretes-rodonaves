#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para inicializar o banco de dados com todos os dados necessários
"""

import os
import sys
import time
import logging
import traceback
from datetime import datetime
from pathlib import Path

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent))

def setup_logging():
    """Configura logging detalhado para debug"""
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

def init_database():
    """Inicializa o banco de dados com todos os dados necessários"""

    logger = setup_logging()
    log_with_timestamp(logger, 'info', "=== INICIANDO CONFIGURACAO COMPLETA DO BANCO DE DADOS ===")
    log_with_timestamp(logger, 'info', f"Python version: {sys.version}")
    log_with_timestamp(logger, 'info', f"Working directory: {os.getcwd()}")
    log_with_timestamp(logger, 'info', f"Script path: {__file__}")

    # Importar após adicionar ao path
    log_with_timestamp(logger, 'info', "Importando módulos essenciais...")
    try:
        from frete_app.db import create_db_and_tables, engine
        from frete_app.seed_data import seed_initial_data
        from sqlmodel import Session, select
        log_with_timestamp(logger, 'info', "Módulos essenciais importados com sucesso")
    except Exception as e:
        log_with_timestamp(logger, 'error', f"ERRO CRITICO ao importar módulos: {e}")
        log_with_timestamp(logger, 'error', f"Traceback: {traceback.format_exc()}")
        return False

    # Criar tabelas
    log_with_timestamp(logger, 'info', "=== ETAPA 1: CRIANDO TABELAS DO BANCO DE DADOS ===")
    try:
        start_time = datetime.utcnow()
        create_db_and_tables()
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        log_with_timestamp(logger, 'info', f"Tabelas criadas com sucesso em {duration:.2f} segundos")
    except Exception as e:
        log_with_timestamp(logger, 'error', f"ERRO CRITICO ao criar tabelas: {e}")
        log_with_timestamp(logger, 'error', f"Traceback: {traceback.format_exc()}")
        return False

    # Popular dados iniciais (produtos, destinos, etc)
    log_with_timestamp(logger, 'info', "=== ETAPA 2: POPULANDO DADOS INICIAIS (PRODUTOS, DESTINOS, ETC) ===")
    try:
        start_time = datetime.utcnow()
        seed_initial_data()
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        log_with_timestamp(logger, 'info', f"Dados iniciais populados com sucesso em {duration:.2f} segundos")
    except Exception as e:
        log_with_timestamp(logger, 'error', f"ERRO ao popular dados iniciais: {e}")
        log_with_timestamp(logger, 'error', f"Traceback: {traceback.format_exc()}")
        log_with_timestamp(logger, 'info', "Continuando mesmo com erro nos dados iniciais...")

    # Importar dados estendidos
    log_with_timestamp(logger, 'info', "=== ETAPA 3: IMPORTANDO DADOS ESTENDIDOS (CIDADES E TARIFAS) ===")
    try:
        log_with_timestamp(logger, 'info', "Verificando se dados de cidades já existem...")

        # Verificar se já tem dados de cidades
        try:
            from frete_app.models_extended import CidadeRodonaves
            log_with_timestamp(logger, 'info', "Modelo CidadeRodonaves importado com sucesso")
        except Exception as e:
            log_with_timestamp(logger, 'error', f"ERRO ao importar modelo CidadeRodonaves: {e}")
            raise

        with Session(engine) as session:
            log_with_timestamp(logger, 'info', "Conectado ao banco, verificando cidades existentes...")
            cidade_count = session.exec(select(CidadeRodonaves)).first()

            if not cidade_count:
                log_with_timestamp(logger, 'info', "Nenhuma cidade encontrada, iniciando importação de dados estendidos...")

                # Importar TDA e TRT
                try:
                    log_with_timestamp(logger, 'info', "Importando módulos TDA e TRT...")
                    from import_tda import import_tda_data
                    from import_trt import import_trt_data
                    log_with_timestamp(logger, 'info', "Módulos TDA e TRT importados com sucesso")

                    # Importar TDA
                    log_with_timestamp(logger, 'info', "Iniciando importação de dados TDA...")
                    start_tda = datetime.utcnow()
                    import_tda_data()
                    end_tda = datetime.utcnow()
                    tda_duration = (end_tda - start_tda).total_seconds()
                    log_with_timestamp(logger, 'info', f"TDA importado com sucesso em {tda_duration:.2f}s")

                    # Importar TRT
                    log_with_timestamp(logger, 'info', "Iniciando importação de dados TRT...")
                    start_trt = datetime.utcnow()
                    import_trt_data()
                    end_trt = datetime.utcnow()
                    trt_duration = (end_trt - start_trt).total_seconds()
                    log_with_timestamp(logger, 'info', f"TRT importado com sucesso em {trt_duration:.2f}s")

                except Exception as e:
                    log_with_timestamp(logger, 'error', f"ERRO ao importar TDA/TRT: {e}")
                    log_with_timestamp(logger, 'error', f"Traceback: {traceback.format_exc()}")
                    log_with_timestamp(logger, 'info', "Continuando sem dados TDA/TRT...")

                # Importar prazos de entrega
                try:
                    log_with_timestamp(logger, 'info', "Tentando importar prazos de entrega...")
                    from import_delivery_times import import_delivery_times
                    start_delivery = datetime.utcnow()
                    import_delivery_times()
                    end_delivery = datetime.utcnow()
                    delivery_duration = (end_delivery - start_delivery).total_seconds()
                    log_with_timestamp(logger, 'info', f"Prazos de entrega importados em {delivery_duration:.2f}s")
                except Exception as e:
                    log_with_timestamp(logger, 'warning', f"Não foi possível importar prazos de entrega: {e}")
                    log_with_timestamp(logger, 'warning', "Continuando sem prazos de entrega...")

                # Contar cidades após importação
                try:
                    total_cidades_apos = len(session.exec(select(CidadeRodonaves)).all())
                    log_with_timestamp(logger, 'info', f"Total de cidades após importação: {total_cidades_apos}")
                except Exception as e:
                    log_with_timestamp(logger, 'warning', f"Não foi possível contar cidades: {e}")
            else:
                # Contar cidades existentes
                try:
                    total_cidades_existentes = len(session.exec(select(CidadeRodonaves)).all())
                    log_with_timestamp(logger, 'info', f"Dados de cidades já existem: {total_cidades_existentes} cidades encontradas")
                    log_with_timestamp(logger, 'info', "Pulando importação de dados estendidos")
                except Exception as e:
                    log_with_timestamp(logger, 'warning', f"Não foi possível contar cidades existentes: {e}")

    except Exception as e:
        log_with_timestamp(logger, 'error', f"ERRO GERAL ao importar dados estendidos: {e}")
        log_with_timestamp(logger, 'error', f"Traceback completo: {traceback.format_exc()}")
        log_with_timestamp(logger, 'info', "Continuando sem dados estendidos...")

    # Verificar integridade
    log_with_timestamp(logger, 'info', "=== ETAPA 4: VERIFICACAO DE INTEGRIDADE DO BANCO ===")
    try:
        log_with_timestamp(logger, 'info', "Importando modelos para verificação...")
        from frete_app.models import Produto, Destino, VersaoTabela, TarifaPeso
        from frete_app.models_extended import Estado, FilialRodonaves
        log_with_timestamp(logger, 'info', "Modelos importados com sucesso")

        with Session(engine) as session:
            log_with_timestamp(logger, 'info', "Iniciando contagem de registros em todas as tabelas...")

            # Contar registros principais
            start_count = datetime.utcnow()
            produtos = len(session.exec(select(Produto)).all())
            destinos = len(session.exec(select(Destino)).all())
            versoes = len(session.exec(select(VersaoTabela)).all())
            tarifas = len(session.exec(select(TarifaPeso)).all())
            end_count = datetime.utcnow()
            count_duration = (end_count - start_count).total_seconds()

            log_with_timestamp(logger, 'info', f"Contagem de tabelas principais concluída em {count_duration:.2f}s")
            log_with_timestamp(logger, 'info', f"=== RESUMO DE TABELAS PRINCIPAIS ===")
            log_with_timestamp(logger, 'info', f"Produtos cadastrados: {produtos}")
            log_with_timestamp(logger, 'info', f"Destinos cadastrados: {destinos}")
            log_with_timestamp(logger, 'info', f"Versões de tabela: {versoes}")
            log_with_timestamp(logger, 'info', f"Tarifas de peso: {tarifas}")

            # Verificar dados estendidos
            try:
                log_with_timestamp(logger, 'info', "Verificando dados estendidos...")
                start_extended = datetime.utcnow()
                estados = len(session.exec(select(Estado)).all())
                filiais = len(session.exec(select(FilialRodonaves)).all())
                cidades = len(session.exec(select(CidadeRodonaves)).all())
                end_extended = datetime.utcnow()
                extended_duration = (end_extended - start_extended).total_seconds()

                log_with_timestamp(logger, 'info', f"Verificação de dados estendidos concluída em {extended_duration:.2f}s")
                log_with_timestamp(logger, 'info', f"=== RESUMO DE DADOS ESTENDIDOS ===")
                log_with_timestamp(logger, 'info', f"Estados cadastrados: {estados}")
                log_with_timestamp(logger, 'info', f"Filiais cadastradas: {filiais}")
                log_with_timestamp(logger, 'info', f"Cidades cadastradas: {cidades}")

                # Avisos para dados estendidos
                if estados == 0:
                    log_with_timestamp(logger, 'warning', "AVISO: Nenhum estado cadastrado")
                if filiais == 0:
                    log_with_timestamp(logger, 'warning', "AVISO: Nenhuma filial cadastrada")
                if cidades == 0:
                    log_with_timestamp(logger, 'warning', "AVISO: Nenhuma cidade cadastrada")

            except Exception as e:
                log_with_timestamp(logger, 'warning', f"Dados estendidos não disponíveis: {e}")
                log_with_timestamp(logger, 'info', "Banco funcionará apenas com dados básicos")
                # Definir valores padrão para cálculos
                estados = filiais = cidades = 0

            # Cálculo de total de registros
            total_registros = produtos + destinos + versoes + tarifas + estados + filiais + cidades
            log_with_timestamp(logger, 'info', f"=== RESUMO GERAL ===")
            log_with_timestamp(logger, 'info', f"Total de registros no banco: {total_registros}")

            # Verificação de integridade crítica
            critical_ok = True
            if produtos == 0:
                log_with_timestamp(logger, 'error', "ERRO CRITICO: Nenhum produto cadastrado!")
                critical_ok = False
            if destinos == 0:
                log_with_timestamp(logger, 'error', "ERRO CRITICO: Nenhum destino cadastrado!")
                critical_ok = False

            if critical_ok:
                log_with_timestamp(logger, 'info', "=== BANCO DE DADOS INICIALIZADO COM SUCESSO! ===")
                return True
            else:
                log_with_timestamp(logger, 'error', "=== FALHA CRITICA NA INICIALIZACAO ===")
                return False

    except Exception as e:
        log_with_timestamp(logger, 'error', f"ERRO CRITICO na verificação de integridade: {e}")
        log_with_timestamp(logger, 'error', f"Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    logger = setup_logging()

    try:
        log_with_timestamp(logger, 'info', "=== INICIANDO SCRIPT DE INICIALIZACAO COMPLETA ===")
        log_with_timestamp(logger, 'info', f"Timestamp de início: {datetime.utcnow().isoformat()}")

        # Aguardar um momento para garantir que o serviço está pronto
        log_with_timestamp(logger, 'info', "Aguardando 2 segundos para estabilização dos serviços...")
        time.sleep(2)

        start_time = datetime.utcnow()
        success = init_database()
        end_time = datetime.utcnow()
        total_duration = (end_time - start_time).total_seconds()

        if success:
            log_with_timestamp(logger, 'info', f"=== INICIALIZACAO COMPLETA CONCLUIDA COM SUCESSO EM {total_duration:.2f}s ===")
            log_with_timestamp(logger, 'info', f"Timestamp de conclusão: {end_time.isoformat()}")
            sys.exit(0)
        else:
            log_with_timestamp(logger, 'error', f"=== FALHA NA INICIALIZACAO APOS {total_duration:.2f}s ===")
            log_with_timestamp(logger, 'error', f"Timestamp de falha: {end_time.isoformat()}")
            sys.exit(1)
    except Exception as e:
        log_with_timestamp(logger, 'error', f"=== ERRO FATAL DURANTE INICIALIZACAO COMPLETA ===")
        log_with_timestamp(logger, 'error', f"Erro: {e}")
        log_with_timestamp(logger, 'error', f"Traceback completo: {traceback.format_exc()}")
        log_with_timestamp(logger, 'error', f"Timestamp de erro fatal: {datetime.utcnow().isoformat()}")
        sys.exit(1)