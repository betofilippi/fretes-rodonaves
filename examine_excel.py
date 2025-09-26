#!/usr/bin/env python
"""
Script para examinar a estrutura do arquivo Excel
"""

import pandas as pd

def examine_excel():
    """Examina a estrutura do arquivo Excel"""
    print("=== EXAMINANDO ESTRUTURA DO EXCEL ===")

    cities_file = "Relação Cidades Atendidas Modal Rodoviário_25_03_25.xlsx"

    try:
        # Ler as primeiras linhas para examinar estrutura
        df = pd.read_excel(cities_file, sheet_name=0, nrows=20)

        print(f"Dimensões do arquivo: {df.shape[0]} linhas x {df.shape[1]} colunas")
        print(f"\nColunas:")
        for i, col in enumerate(df.columns):
            print(f"  {i}: {col}")

        print(f"\nPrimeiras 10 linhas:")
        for idx, row in df.iterrows():
            if idx < 10:
                print(f"\nLinha {idx}:")
                for i in range(min(15, len(row))):  # Mostrar primeiras 15 colunas
                    value = str(row.iloc[i])[:20] if pd.notna(row.iloc[i]) else "NaN"
                    print(f"  Col {i}: {value}")

    except Exception as e:
        print(f"Erro ao examinar Excel: {e}")

if __name__ == "__main__":
    examine_excel()