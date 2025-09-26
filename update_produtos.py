#!/usr/bin/env python3
"""Script para atualizar valores NF padrão dos produtos existentes"""

from sqlmodel import Session, select
from frete_app.db import engine
from frete_app.models import Produto

# Valores corretos para frete (não preço da embalagem)
valores_corretos = {
    "Zilla": 1500.00,
    "Juna": 2500.00,
    "Kimbo": 2500.00,
    "Kay": 3000.00,  # Mais pesado
    "Jaya": 2200.00
}

def atualizar_produtos():
    with Session(engine) as session:
        produtos = session.exec(select(Produto)).all()

        for produto in produtos:
            if produto.nome in valores_corretos:
                old_value = produto.valor_nf_padrao
                produto.valor_nf_padrao = valores_corretos[produto.nome]
                print(f"Produto {produto.nome}: R$ {old_value:.2f} -> R$ {produto.valor_nf_padrao:.2f}")

        session.commit()
        print(f"✅ Atualizados {len(produtos)} produtos com valores corretos para cálculo de frete")

if __name__ == "__main__":
    atualizar_produtos()