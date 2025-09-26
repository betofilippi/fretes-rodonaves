#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script FORÇADO para importar TODAS AS CIDADES DOS EXCEL
VERSÃO CORRIGIDA PARA RAILWAY - IMPORTA TODAS AS 4000+ CIDADES
"""

import os
import sys
import pandas as pd
import logging
import traceback
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple

# Configurar encoding para UTF-8 (Railway compatibility)
if hasattr(sys, 'stdout') and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass

# Configurar logging detalhado
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('import_cities.log', mode='w', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

# Adicionar o diretório raiz ao path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from frete_app.db import engine, create_db_and_tables
    from sqlmodel import Session, select
    from frete_app.models import Destino
    from frete_app.models_extended import Estado, FilialRodonaves
except ImportError as e:
    logger.error(f"Erro ao importar módulos: {e}")
    sys.exit(1)


class CityImporter:
    """Importador robusto de cidades para Railway"""

    def __init__(self):
        self.total_imported = 0
        self.errors = []
        self.warnings = []
        self.city_cache = {}

    def log_progress(self, message: str, level: str = "INFO"):
        """Log com timestamp e level"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        if level == "INFO":
            logger.info(f"[{timestamp}] {message}")
        elif level == "ERROR":
            logger.error(f"[{timestamp}] {message}")
            self.errors.append(message)
        elif level == "WARNING":
            logger.warning(f"[{timestamp}] {message}")
            self.warnings.append(message)

        # Progress visual no console
        if self.total_imported > 0 and self.total_imported % 500 == 0:
            print(f"\n🔄 Progress: {self.total_imported} cidades importadas...")

    def find_excel_files(self) -> Dict[str, str]:
        """Localiza arquivos Excel com verificação robusta"""
        files = {}

        # Lista de possíveis nomes/padrões para os arquivos
        patterns = {
            'cities': [
                'Relação Cidades Atendidas Modal Rodoviário_25_03_25.xlsx',
                'Relacao Cidades*.xlsx',
                '*Modal Rodoviario*.xlsx',
                '*Cidades Atendidas*.xlsx'
            ],
            'tda': [
                'TDAs e TRTs 2025 11_04_25 - NXT.xlsx',
                'TDA*.xlsx',
                'TRTs*.xlsx',
                '*TDA*.xlsx'
            ]
        }

        # Procurar no diretório atual e subdiretórios
        search_dirs = [
            project_root,
            project_root / 'data',
            project_root / 'frete_app' / 'data',
            Path('.'),
            Path('./data')
        ]

        for search_dir in search_dirs:
            if not search_dir.exists():
                continue

            self.log_progress(f"Procurando arquivos Excel em: {search_dir}")

            for file_type, pattern_list in patterns.items():
                if file_type in files:
                    continue

                for pattern in pattern_list:
                    matches = list(search_dir.glob(pattern))
                    if matches:
                        file_path = str(matches[0])
                        files[file_type] = file_path
                        self.log_progress(f"Encontrado {file_type}: {file_path}")
                        break

        return files

    def validate_excel_file(self, file_path: str) -> bool:
        """Valida se o arquivo Excel é válido e acessível"""
        try:
            if not os.path.exists(file_path):
                self.log_progress(f"Arquivo não encontrado: {file_path}", "ERROR")
                return False

            # Tentar ler o arquivo
            pd.read_excel(file_path, sheet_name=0, nrows=1)
            file_size = os.path.getsize(file_path)

            self.log_progress(f"Arquivo validado: {file_path} ({file_size} bytes)")
            return True

        except Exception as e:
            self.log_progress(f"Erro ao validar arquivo {file_path}: {e}", "ERROR")
            return False

    def clean_string(self, value: Any) -> str:
        """Limpa e normaliza strings"""
        if pd.isna(value) or value is None:
            return ""

        try:
            # Converter para string e limpar
            result = str(value).strip().upper()
            # Remover caracteres especiais problemáticos
            result = result.replace('\x00', '').replace('\n', ' ').replace('\r', ' ')
            # Normalizar espaços
            result = ' '.join(result.split())
            return result
        except Exception:
            return ""

    def extract_cep(self, value: Any) -> str:
        """Extrai e formata CEP"""
        if pd.isna(value) or value is None:
            return ""

        try:
            cep = str(value).strip().replace('-', '').replace('.', '')
            # Se for número, formatar
            if cep.isdigit() and len(cep) == 8:
                return f"{cep[:5]}-{cep[5:]}"
            elif cep.isdigit() and len(cep) == 5:
                return f"{cep}-000"
            # Se já tem formato, manter
            elif '-' in str(value):
                return str(value).strip()
            return cep
        except Exception:
            return ""

    def extract_prazo(self, value: Any) -> Optional[int]:
        """Extrai prazo em dias"""
        if pd.isna(value) or value is None:
            return None

        try:
            # Tentar converter diretamente
            if isinstance(value, (int, float)):
                return int(value) if value > 0 else None

            # Se for string, tentar extrair número
            value_str = str(value).replace(',', '.').strip()
            if value_str.replace('.', '').isdigit():
                return int(float(value_str)) if float(value_str) > 0 else None

        except Exception:
            pass

        return None

    def import_from_cities_file(self, file_path: str, session: Session) -> int:
        """Importa cidades do arquivo principal de cidades"""
        self.log_progress(f"Iniciando importação de {file_path}")

        try:
            # Ler arquivo com encoding robusto
            df = pd.read_excel(file_path, sheet_name=0, dtype=str)
            self.log_progress(f"Arquivo carregado: {len(df)} linhas, {len(df.columns)} colunas")

            imported_count = 0
            city_dict = {}

            # Processar cada linha (pular cabeçalhos)
            for idx, row in df.iterrows():
                if idx < 3:  # Pular cabeçalhos
                    continue

                try:
                    # Extrair dados da linha baseado na estrutura identificada
                    # Colunas: 0-código origem, 1-cidade origem, 2-uf origem,
                    #          7-cidade destino, 8-uf destino, 9-cep inicial, 10-cep final
                    #          15-prazo min, 16-prazo max

                    cidade_nome = self.clean_string(row.iloc[7]) if len(row) > 7 else ""
                    uf = self.clean_string(row.iloc[8]) if len(row) > 8 else ""

                    if not cidade_nome or not uf or len(uf) != 2:
                        continue

                    # CEPs
                    cep_ini = self.extract_cep(row.iloc[9]) if len(row) > 9 else ""
                    cep_fim = self.extract_cep(row.iloc[10]) if len(row) > 10 else ""

                    # Prazos
                    prazo_min = self.extract_prazo(row.iloc[15]) if len(row) > 15 else None
                    prazo_max = self.extract_prazo(row.iloc[16]) if len(row) > 16 else None

                    # Tipo de transporte
                    tipo_transporte = "RODOVIARIO"
                    if len(row) > 11 and pd.notna(row.iloc[11]):
                        modal = self.clean_string(row.iloc[11])
                        if "FLUV" in modal:
                            tipo_transporte = "FLUVIAL"
                        elif "AERE" in modal or "AEREO" in modal:
                            tipo_transporte = "AEREO"

                    # Chave única para evitar duplicatas
                    key = f"{uf}_{cidade_nome}"

                    # Se cidade já existe no dicionário, atualizar com melhores dados
                    if key in city_dict:
                        existing = city_dict[key]
                        if prazo_min:
                            existing['prazo_min'] = prazo_min
                        if prazo_max:
                            existing['prazo_max'] = prazo_max
                        if cep_ini and cep_ini != "00000-000":
                            existing['cep_ini'] = cep_ini
                        if cep_fim and cep_fim != "99999-999":
                            existing['cep_fim'] = cep_fim
                    else:
                        # Nova cidade
                        city_dict[key] = {
                            'uf': uf,
                            'nome': cidade_nome,
                            'cep_ini': cep_ini or "00000-000",
                            'cep_fim': cep_fim or "99999-999",
                            'prazo_min': prazo_min,
                            'prazo_max': prazo_max,
                            'tipo': tipo_transporte
                        }

                except Exception as e:
                    self.log_progress(f"Erro ao processar linha {idx}: {e}", "WARNING")
                    continue

            # Inserir todas as cidades no banco
            for key, data in city_dict.items():
                try:
                    # Verificar se já existe
                    existing = session.exec(
                        select(Destino).where(
                            Destino.uf == data['uf'],
                            Destino.cidade == data['nome']
                        )
                    ).first()

                    if existing:
                        continue  # Já existe

                    # Determinar categoria baseada no tipo de transporte e dados
                    categoria = "INTERIOR"
                    if data['tipo'] == "FLUVIAL":
                        categoria = "FLUVIAL"
                    elif data['tipo'] == "AEREO":
                        categoria = "AEREO"
                    elif data['nome'] and ("CAPITAL" in data['nome'] or data['nome'] in ["SAO PAULO", "RIO DE JANEIRO", "BELO HORIZONTE", "SALVADOR", "FORTALEZA", "BRASILIA", "RECIFE", "PORTO ALEGRE", "MANAUS", "CURITIBA", "GOIANIA"]):
                        categoria = "CAPITAL"

                    destino = Destino(
                        uf=data['uf'],
                        cidade=data['nome'],
                        categoria=categoria
                    )

                    session.add(destino)
                    imported_count += 1
                    self.total_imported += 1

                    # Commit a cada 200 registros
                    if imported_count % 200 == 0:
                        session.commit()
                        self.log_progress(f"Importadas {imported_count} cidades do arquivo principal")

                except Exception as e:
                    self.log_progress(f"Erro ao inserir cidade {key}: {e}", "WARNING")
                    continue

            # Commit final
            session.commit()
            self.log_progress(f"Importação concluída: {imported_count} cidades do arquivo principal")
            return imported_count

        except Exception as e:
            self.log_progress(f"Erro ao importar arquivo de cidades: {e}", "ERROR")
            logger.error(traceback.format_exc())
            return 0

    def import_from_tda_file(self, file_path: str, session: Session) -> int:
        """Importa cidades adicionais do arquivo TDA"""
        self.log_progress(f"Verificando cidades adicionais em {file_path}")

        try:
            # Tentar diferentes abas
            sheets_to_try = ["TDAs-TRTs", "TDA", "TDA Simplificada", 0]
            df = None

            for sheet in sheets_to_try:
                try:
                    df = pd.read_excel(file_path, sheet_name=sheet, dtype=str)
                    self.log_progress(f"Usando aba: {sheet}")
                    break
                except Exception:
                    continue

            if df is None:
                self.log_progress("Não foi possível ler nenhuma aba do arquivo TDA", "ERROR")
                return 0

            imported_count = 0

            # Processar cada linha
            for idx, row in df.iterrows():
                try:
                    # Estrutura TDA: CIDADE (col 2), UF (col 3), CEP Inicial (col 8), CEP Final (col 9), VALOR (col 5)
                    cidade_nome = self.clean_string(row.iloc[2]) if len(row) > 2 else ""
                    uf = self.clean_string(row.iloc[3]) if len(row) > 3 else ""

                    if not cidade_nome or not uf or len(uf) != 2:
                        continue

                    # Verificar se cidade já existe
                    existing = session.exec(
                        select(Destino).where(
                            Destino.uf == uf,
                            Destino.cidade == cidade_nome
                        )
                    ).first()

                    if existing:
                        continue  # Já existe

                    # Determinar categoria
                    categoria = "INTERIOR"
                    if cidade_nome and ("CAPITAL" in cidade_nome or cidade_nome in ["SAO PAULO", "RIO DE JANEIRO", "BELO HORIZONTE", "SALVADOR", "FORTALEZA", "BRASILIA", "RECIFE", "PORTO ALEGRE", "MANAUS", "CURITIBA", "GOIANIA"]):
                        categoria = "CAPITAL"

                    # Criar novo destino
                    destino = Destino(
                        uf=uf,
                        cidade=cidade_nome,
                        categoria=categoria
                    )

                    session.add(destino)
                    imported_count += 1
                    self.total_imported += 1

                    # Commit a cada 100 registros
                    if imported_count % 100 == 0:
                        session.commit()
                        self.log_progress(f"Adicionadas {imported_count} cidades do TDA")

                except Exception as e:
                    self.log_progress(f"Erro ao processar linha TDA {idx}: {e}", "WARNING")
                    continue

            # Commit final
            session.commit()
            self.log_progress(f"TDA concluído: {imported_count} cidades adicionais")
            return imported_count

        except Exception as e:
            self.log_progress(f"Erro ao importar arquivo TDA: {e}", "ERROR")
            logger.error(traceback.format_exc())
            return 0

    def create_backup(self, session: Session) -> bool:
        """Cria backup das cidades existentes"""
        try:
            existing_cities = session.exec(select(Destino)).all()
            if existing_cities:
                backup_file = f"cities_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
                with open(backup_file, 'w', encoding='utf-8') as f:
                    f.write(f"Backup criado em: {datetime.now()}\n")
                    f.write(f"Total de cidades: {len(existing_cities)}\n\n")
                    for cidade in existing_cities:
                        f.write(f"{cidade.uf}|{cidade.cidade}|{cidade.categoria}\n")

                self.log_progress(f"Backup criado: {backup_file} ({len(existing_cities)} cidades)")
                return True
            return True
        except Exception as e:
            self.log_progress(f"Erro ao criar backup: {e}", "ERROR")
            return False

    def force_import_all_cities(self) -> bool:
        """Executa importação completa e forçada de todas as cidades"""

        self.log_progress("=" * 60)
        self.log_progress("INICIANDO IMPORTAÇÃO COMPLETA DE TODAS AS CIDADES")
        self.log_progress("=" * 60)

        try:
            # 1. Criar tabelas se necessário
            create_db_and_tables()
            self.log_progress("Tabelas do banco verificadas/criadas")

            with Session(engine) as session:
                # 2. Criar backup das cidades existentes
                if not self.create_backup(session):
                    self.log_progress("Falha ao criar backup - continuando mesmo assim", "WARNING")

                # 3. Limpar cidades existentes
                existing = session.exec(select(Destino)).all()
                if existing:
                    self.log_progress(f"Removendo {len(existing)} cidades existentes...")
                    for cidade in existing:
                        session.delete(cidade)
                    session.commit()
                    self.log_progress("Cidades antigas removidas")

                # 5. Localizar arquivos Excel
                excel_files = self.find_excel_files()

                if not excel_files:
                    self.log_progress("NENHUM ARQUIVO EXCEL ENCONTRADO!", "ERROR")
                    return False

                # 6. Validar arquivos
                valid_files = {}
                for file_type, file_path in excel_files.items():
                    if self.validate_excel_file(file_path):
                        valid_files[file_type] = file_path
                    else:
                        self.log_progress(f"Arquivo inválido: {file_path}", "ERROR")

                if not valid_files:
                    self.log_progress("NENHUM ARQUIVO EXCEL VÁLIDO!", "ERROR")
                    return False

                # 4. Importar do arquivo principal de cidades
                cities_imported = 0
                if 'cities' in valid_files:
                    cities_imported = self.import_from_cities_file(
                        valid_files['cities'], session
                    )

                # 5. Importar cidades adicionais do TDA
                tda_imported = 0
                if 'tda' in valid_files:
                    tda_imported = self.import_from_tda_file(
                        valid_files['tda'], session
                    )

                # 6. Verificação final
                final_count = len(session.exec(select(Destino)).all())

                # 7. Relatório final
                self.log_progress("=" * 60)
                self.log_progress("RELATÓRIO FINAL DA IMPORTAÇÃO")
                self.log_progress("=" * 60)
                self.log_progress(f"Cidades do arquivo principal: {cities_imported}")
                self.log_progress(f"Cidades adicionais do TDA: {tda_imported}")
                self.log_progress(f"TOTAL DE CIDADES IMPORTADAS: {self.total_imported}")
                self.log_progress(f"TOTAL DE CIDADES NO BANCO: {final_count}")

                if self.warnings:
                    self.log_progress(f"Warnings encontrados: {len(self.warnings)}")

                if self.errors:
                    self.log_progress(f"Erros encontrados: {len(self.errors)}", "ERROR")

                # 8. Validação crítica
                if final_count < 3000:
                    self.log_progress("=" * 60, "ERROR")
                    self.log_progress("FALHA CRÍTICA: MENOS DE 3000 CIDADES IMPORTADAS!", "ERROR")
                    self.log_progress("VERIFIQUE OS ARQUIVOS EXCEL E TENTE NOVAMENTE!", "ERROR")
                    self.log_progress("=" * 60, "ERROR")
                    return False

                self.log_progress("=" * 60)
                self.log_progress("✅ IMPORTAÇÃO COMPLETA REALIZADA COM SUCESSO!")
                self.log_progress(f"✅ {final_count} CIDADES DISPONÍVEIS NO SISTEMA")
                self.log_progress("=" * 60)

                return True

        except Exception as e:
            self.log_progress(f"ERRO CRÍTICO NA IMPORTAÇÃO: {e}", "ERROR")
            logger.error(traceback.format_exc())
            return False


def main():
    """Função principal"""
    importer = CityImporter()

    try:
        success = importer.force_import_all_cities()

        if success:
            print(f"\n🎉 SUCESSO! {importer.total_imported} cidades importadas!")
            sys.exit(0)
        else:
            print(f"\n❌ FALHA! Verifique os logs para detalhes.")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n⚠️  Importação cancelada pelo usuário")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Erro inesperado: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()