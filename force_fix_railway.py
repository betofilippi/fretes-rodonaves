#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SCRIPT DE CORREÇÃO FORÇADA PARA RAILWAY
Este script FORÇA a população correta de produtos e estados
"""

import os
import sys
sys.path.insert(0, '.')

from sqlmodel import Session, select, SQLModel
from frete_app.db import engine

print("\n" + "="*60)
print("INICIANDO CORREÇÃO FORÇADA DO RAILWAY")
print("="*60)

# Importar modelos
try:
    from frete_app.models import Produto, Destino
    from frete_app.models_extended import Estado
    print("[OK] Modelos importados com sucesso")
except Exception as e:
    print(f"[ERRO] Erro ao importar modelos: {e}")
    sys.exit(1)

# Criar todas as tabelas
SQLModel.metadata.create_all(engine)
print("[OK] Tabelas verificadas/criadas")

with Session(engine) as session:
    print("\n--- VERIFICANDO ESTADO ATUAL ---")

    # Verificar produtos
    produtos_count = len(session.exec(select(Produto)).all())
    print(f"Produtos existentes: {produtos_count}")

    # Verificar estados
    try:
        estados_count = len(session.exec(select(Estado)).all())
        print(f"Estados existentes: {estados_count}")
    except:
        estados_count = 0
        print("Estados: Tabela não existe ou erro")

    # Verificar cidades
    cidades_count = len(session.exec(select(Destino)).all())
    print(f"Cidades (Destino) existentes: {cidades_count}")

    print("\n--- INICIANDO POPULAÇÃO FORÇADA ---")

    # FORÇAR CRIAÇÃO DE PRODUTOS
    if produtos_count < 8:
        print("\n[1/3] Populando PRODUTOS...")

        # Deletar produtos existentes se houver poucos
        if produtos_count > 0:
            session.query(Produto).delete()
            session.commit()
            print("  → Produtos antigos removidos")

        produtos_data = [
            {'nome': 'Zilla', 'largura_cm': 72.0, 'altura_cm': 53.0,
             'profundidade_cm': 130.0, 'peso_real_kg': 50.0, 'valor_nf_padrao': 1500.0},
            {'nome': 'Juna', 'largura_cm': 78.0, 'altura_cm': 186.0,
             'profundidade_cm': 128.0, 'peso_real_kg': 123.0, 'valor_nf_padrao': 2500.0},
            {'nome': 'Kimbo', 'largura_cm': 78.0, 'altura_cm': 186.0,
             'profundidade_cm': 128.0, 'peso_real_kg': 121.0, 'valor_nf_padrao': 2500.0},
            {'nome': 'Kay', 'largura_cm': 78.0, 'altura_cm': 186.0,
             'profundidade_cm': 128.0, 'peso_real_kg': 161.0, 'valor_nf_padrao': 3000.0},
            {'nome': 'Jaya', 'largura_cm': 78.0, 'altura_cm': 186.0,
             'profundidade_cm': 128.0, 'peso_real_kg': 107.0, 'valor_nf_padrao': 2200.0}
        ]

        for prod_data in produtos_data:
            produto = Produto(**prod_data)
            session.add(produto)
            print(f"  → Adicionado: {prod_data['nome']}")

        session.commit()
        print(f"  [OK] {len(produtos_data)} produtos criados com sucesso!")
    else:
        print("\n[1/3] Produtos já populados [OK]")

    # FORÇAR CRIAÇÃO DE ESTADOS
    if estados_count < 27:
        print("\n[2/3] Populando ESTADOS...")

        # Deletar estados existentes se houver poucos
        if estados_count > 0:
            session.query(Estado).delete()
            session.commit()
            print("  → Estados antigos removidos")

        estados_brasil = [
            ('AC', 'Acre', 'Norte'),
            ('AL', 'Alagoas', 'Nordeste'),
            ('AP', 'Amapá', 'Norte'),
            ('AM', 'Amazonas', 'Norte'),
            ('BA', 'Bahia', 'Nordeste'),
            ('CE', 'Ceará', 'Nordeste'),
            ('DF', 'Distrito Federal', 'Centro-Oeste'),
            ('ES', 'Espírito Santo', 'Sudeste'),
            ('GO', 'Goiás', 'Centro-Oeste'),
            ('MA', 'Maranhão', 'Nordeste'),
            ('MT', 'Mato Grosso', 'Centro-Oeste'),
            ('MS', 'Mato Grosso do Sul', 'Centro-Oeste'),
            ('MG', 'Minas Gerais', 'Sudeste'),
            ('PA', 'Pará', 'Norte'),
            ('PB', 'Paraíba', 'Nordeste'),
            ('PR', 'Paraná', 'Sul'),
            ('PE', 'Pernambuco', 'Nordeste'),
            ('PI', 'Piauí', 'Nordeste'),
            ('RJ', 'Rio de Janeiro', 'Sudeste'),
            ('RN', 'Rio Grande do Norte', 'Nordeste'),
            ('RS', 'Rio Grande do Sul', 'Sul'),
            ('RO', 'Rondônia', 'Norte'),
            ('RR', 'Roraima', 'Norte'),
            ('SC', 'Santa Catarina', 'Sul'),
            ('SP', 'São Paulo', 'Sudeste'),
            ('SE', 'Sergipe', 'Nordeste'),
            ('TO', 'Tocantins', 'Norte')
        ]

        for sigla, nome, regiao in estados_brasil:
            estado = Estado(
                sigla=sigla,
                nome=nome,
                regiao=regiao,
                tem_cobertura=True
            )
            session.add(estado)
            print(f"  → Adicionado: {sigla} - {nome}")

        session.commit()
        print(f"  [OK] {len(estados_brasil)} estados criados com sucesso!")
    else:
        print("\n[2/3] Estados já populados [OK]")

    # Verificar cidades (não vamos mexer se já tem muitas)
    if cidades_count > 1000:
        print(f"\n[3/3] Cidades já populadas ({cidades_count} cidades) [OK]")
    else:
        print(f"\n[3/3] Cidades: {cidades_count} (manter como está)")

    # VERIFICAÇÃO FINAL
    print("\n--- VERIFICAÇÃO FINAL ---")

    produtos_final = len(session.exec(select(Produto)).all())
    estados_final = len(session.exec(select(Estado)).all())
    cidades_final = len(session.exec(select(Destino)).all())

    print(f"[OK] Produtos: {produtos_final}")
    print(f"[OK] Estados: {estados_final}")
    print(f"[OK] Cidades: {cidades_final}")

    # Validar
    if produtos_final >= 8 and estados_final >= 27:
        print("\n" + "="*60)
        print("[OK][OK][OK] CORREÇÃO CONCLUÍDA COM SUCESSO! [OK][OK][OK]")
        print("="*60)
        sys.exit(0)
    else:
        print("\n" + "="*60)
        print("[ERRO][ERRO][ERRO] ERRO: Ainda faltam dados! [ERRO][ERRO][ERRO]")
        print("="*60)
        sys.exit(1)