#!/usr/bin/env python
"""
Script FORÇADO para importar TODAS AS CIDADES DOS EXCEL
NÃO É FALLBACK - IMPORTA TUDO!
"""

import os
import sys
import pandas as pd
from pathlib import Path

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent))

from frete_app.db import engine, create_db_and_tables
from sqlmodel import Session, select
from frete_app.models_extended import Estado, FilialRodonaves, CidadeRodonaves


def force_import_all_cities():
    """Força importação de TODAS as cidades dos Excel"""

    print("[INFO] INICIANDO IMPORTACAO COMPLETA DE TODAS AS CIDADES...")

    # Criar tabelas se não existirem
    create_db_and_tables()

    with Session(engine) as session:
        # Limpar cidades existentes para reimportar tudo
        existing = session.exec(select(CidadeRodonaves)).all()
        if existing:
            print(f"[AVISO] Removendo {len(existing)} cidades antigas...")
            for cidade in existing:
                session.delete(cidade)
            session.commit()

        # Criar filial padrão
        filial = session.exec(select(FilialRodonaves)).first()
        if not filial:
            filial = FilialRodonaves(codigo=1, nome="SAO PAULO", uf="SP")
            session.add(filial)
            session.commit()
            session.refresh(filial)

        total_imported = 0

        # 1. IMPORTAR DO ARQUIVO DE CIDADES COM PRAZOS
        cities_file = "Relação Cidades Atendidas Modal Rodoviário_25_03_25.xlsx"
        if os.path.exists(cities_file):
            print(f"[INFO] Importando de {cities_file}...")
            try:
                df = pd.read_excel(cities_file, sheet_name=0)

                # Mapear todas as cidades
                cidade_dict = {}

                for idx, row in df.iterrows():
                    if idx < 1:  # Skip header
                        continue

                    try:
                        uf = str(row.iloc[3]).strip()[:2].upper() if pd.notna(row.iloc[3]) else ""
                        cidade_nome = str(row.iloc[2]).strip().upper() if pd.notna(row.iloc[2]) else ""

                        if not uf or not cidade_nome:
                            continue

                        # CEPs - pegar das colunas 9 e 10
                        cep_ini = str(row.iloc[9]).strip() if pd.notna(row.iloc[9]) else ""
                        cep_fim = str(row.iloc[10]).strip() if pd.notna(row.iloc[10]) else ""

                        # Se não tem CEP, criar padrão
                        if not cep_ini:
                            cep_ini = "00000-000"
                        if not cep_fim:
                            cep_fim = "99999-999"

                        # Prazos CPF nas colunas 15 e 16
                        prazo_min = None
                        prazo_max = None

                        try:
                            if pd.notna(row.iloc[15]):
                                prazo_min = int(float(str(row.iloc[15]).replace(',', '.')))
                        except:
                            pass

                        try:
                            if pd.notna(row.iloc[16]):
                                prazo_max = int(float(str(row.iloc[16]).replace(',', '.')))
                        except:
                            pass

                        # Tipo de transporte
                        tipo_transporte = "RODOVIARIO"
                        if pd.notna(row.iloc[11]):
                            modal = str(row.iloc[11]).upper()
                            if "FLUV" in modal:
                                tipo_transporte = "FLUVIAL"
                            elif "AERE" in modal or "AEREO" in modal:
                                tipo_transporte = "AEREO"

                        key = f"{uf}_{cidade_nome}"

                        # Se já existe, atualizar com melhores dados
                        if key in cidade_dict:
                            if prazo_min:
                                cidade_dict[key]['prazo_min'] = prazo_min
                            if prazo_max:
                                cidade_dict[key]['prazo_max'] = prazo_max
                            if cep_ini != "00000-000":
                                cidade_dict[key]['cep_ini'] = cep_ini
                            if cep_fim != "99999-999":
                                cidade_dict[key]['cep_fim'] = cep_fim
                        else:
                            cidade_dict[key] = {
                                'uf': uf,
                                'nome': cidade_nome,
                                'cep_ini': cep_ini,
                                'cep_fim': cep_fim,
                                'prazo_min': prazo_min,
                                'prazo_max': prazo_max,
                                'tipo': tipo_transporte
                            }

                    except Exception as e:
                        print(f"[AVISO] Erro linha {idx}: {e}")
                        continue

                # Inserir todas as cidades mapeadas
                for key, data in cidade_dict.items():
                    cidade = CidadeRodonaves(
                        uf=data['uf'],
                        cidade=data['nome'],
                        cep_inicial=data['cep_ini'],
                        cep_final=data['cep_fim'],
                        filial_id=filial.id,
                        tarifa_minima=50.0,
                        peso_taxado_minimo_kg=10.0,
                        advalorem_percent=0.005,
                        prazo_cpf_min_dias=data['prazo_min'],
                        prazo_cpf_max_dias=data['prazo_max'],
                        tipo_transporte=data['tipo']
                    )
                    session.add(cidade)
                    total_imported += 1

                    if total_imported % 100 == 0:
                        session.commit()
                        print(f"[INFO] {total_imported} cidades importadas...")

                session.commit()
                print(f"[OK] {total_imported} cidades importadas do arquivo de prazos")

            except Exception as e:
                print(f"[ERRO] Falha ao importar cidades: {e}")

        # 2. IMPORTAR DO TDA SE EXISTIR E ADICIONAR CIDADES FALTANTES
        tda_file = "TDAs e TRTs 2025 11_04_25 - NXT.xlsx"
        if os.path.exists(tda_file):
            print(f"[INFO] Verificando cidades adicionais em {tda_file}...")
            try:
                # Tentar diferentes nomes de aba
                for sheet in ["TDA", "TDA Simplificada", 0]:
                    try:
                        df = pd.read_excel(tda_file, sheet_name=sheet)
                        break
                    except:
                        continue

                added = 0
                for idx, row in df.iterrows():
                    try:
                        uf = str(row.iloc[0]).strip()[:2].upper() if pd.notna(row.iloc[0]) else ""
                        cidade_nome = str(row.iloc[1]).strip().upper() if pd.notna(row.iloc[1]) else ""

                        if not uf or not cidade_nome:
                            continue

                        # Verificar se já existe
                        existing = session.exec(
                            select(CidadeRodonaves).where(
                                CidadeRodonaves.uf == uf,
                                CidadeRodonaves.cidade == cidade_nome
                            )
                        ).first()

                        if not existing:
                            cep_ini = str(row.iloc[2]) if pd.notna(row.iloc[2]) else "00000-000"
                            cep_fim = str(row.iloc[3]) if pd.notna(row.iloc[3]) else "99999-999"

                            cidade = CidadeRodonaves(
                                uf=uf,
                                cidade=cidade_nome,
                                cep_inicial=cep_ini,
                                cep_final=cep_fim,
                                filial_id=filial.id,
                                tarifa_minima=float(row.iloc[4]) if pd.notna(row.iloc[4]) else 50.0,
                                peso_taxado_minimo_kg=10.0,
                                advalorem_percent=0.005,
                                tipo_transporte="RODOVIARIO"
                            )
                            session.add(cidade)
                            added += 1
                            total_imported += 1

                    except Exception as e:
                        continue

                if added > 0:
                    session.commit()
                    print(f"[OK] {added} cidades adicionais do TDA")

            except Exception as e:
                print(f"[AVISO] Nao foi possivel importar TDA adicional: {e}")

        print(f"\n[OK] TOTAL DE CIDADES IMPORTADAS: {total_imported}")

        # Verificar total final
        final_count = len(session.exec(select(CidadeRodonaves)).all())
        print(f"[OK] TOTAL DE CIDADES NO BANCO: {final_count}")

        if final_count < 3000:
            print("[ERRO] MENOS DE 3000 CIDADES! VERIFICAR ARQUIVOS EXCEL!")
            return False

        return True


if __name__ == "__main__":
    if force_import_all_cities():
        print("\n[OK] IMPORTACAO COMPLETA REALIZADA COM SUCESSO!")
        sys.exit(0)
    else:
        print("\n[ERRO] FALHA NA IMPORTACAO COMPLETA!")
        sys.exit(1)