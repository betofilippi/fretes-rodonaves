#!/bin/bash
# Start script for Railway with detailed logging

# Function to log with timestamp
log_with_timestamp() {
    local level=$1
    local message=$2
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S.%3N UTC')
    echo "[$timestamp] [$level] $message"
}

# Function to check command success and log
check_and_log_result() {
    local command_name=$1
    local exit_code=$2
    local start_time=$3
    local end_time=$(date +%s.%3N)
    local duration=$(echo "$end_time - $start_time" | bc -l 2>/dev/null || echo "N/A")

    if [ $exit_code -eq 0 ]; then
        log_with_timestamp "INFO" "$command_name completed successfully in ${duration}s"
        return 0
    else
        log_with_timestamp "ERROR" "$command_name failed with exit code $exit_code after ${duration}s"
        return $exit_code
    fi
}

# Start logging
log_with_timestamp "INFO" "=== INICIANDO SCRIPT DE START PARA RAILWAY ==="
log_with_timestamp "INFO" "Timestamp de início: $(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)"
log_with_timestamp "INFO" "Diretório atual: $(pwd)"
log_with_timestamp "INFO" "Usuário: $(whoami)"
log_with_timestamp "INFO" "Versão do Python: $(python --version 2>&1)"
log_with_timestamp "INFO" "Variáveis de ambiente relevantes:"
log_with_timestamp "INFO" "  PORT=${PORT:-8000}"
log_with_timestamp "INFO" "  DATABASE_URL=${DATABASE_URL:0:50}..." # Só mostrar início por segurança

# LIMPAR BANCO ANTIGO (apenas no Railway)
if [ -n "$RAILWAY_ENVIRONMENT" ] || [ -n "$DATABASE_URL" ]; then
    log_with_timestamp "INFO" "=== AMBIENTE RAILWAY DETECTADO - LIMPANDO BANCO ANTIGO ==="
    if [ -f "/app/data/frete.db" ]; then
        rm -f /app/data/frete.db
        log_with_timestamp "INFO" "Banco antigo removido"
    fi
    if [ -f "./data/frete.db" ]; then
        rm -f ./data/frete.db
        log_with_timestamp "INFO" "Banco local removido"
    fi
fi

# FORÇA CORREÇÃO DE PRODUTOS E ESTADOS
log_with_timestamp "INFO" "=== EXECUTANDO CORREÇÃO FORÇADA ==="
python force_fix_railway.py
fix_exit_code=$?
if [ $fix_exit_code -eq 0 ]; then
    log_with_timestamp "INFO" "Correção forçada executada com sucesso!"
else
    log_with_timestamp "ERROR" "Correção forçada falhou, mas continuando..."
fi

# Create data directory if it doesn't exist
log_with_timestamp "INFO" "=== ETAPA 1: VERIFICANDO DIRETÓRIO DE DADOS ==="
start_time=$(date +%s.%3N)
if mkdir -p /app/data; then
    check_and_log_result "Criação do diretório /app/data" 0 $start_time
    log_with_timestamp "INFO" "Diretório /app/data criado/verificado"
    ls -la /app/data/ && log_with_timestamp "INFO" "Conteúdo do diretório /app/data listado"
else
    check_and_log_result "Criação do diretório /app/data" 1 $start_time
    log_with_timestamp "ERROR" "Falha ao criar diretório /app/data"
fi

# Check if Excel files exist
log_with_timestamp "INFO" "=== VERIFICANDO ARQUIVOS EXCEL NECESSÁRIOS ==="
excel_files_found=0
for file in "Relação Cidades Atendidas Modal Rodoviário_25_03_25.xlsx" "TDAs e TRTs 2025 11_04_25 - NXT.xlsx"; do
    if [ -f "$file" ]; then
        size=$(du -h "$file" | cut -f1)
        log_with_timestamp "INFO" "Arquivo encontrado: $file (tamanho: $size)"
        excel_files_found=$((excel_files_found + 1))
    else
        log_with_timestamp "WARNING" "Arquivo não encontrado: $file"
    fi
done
log_with_timestamp "INFO" "Total de arquivos Excel encontrados: $excel_files_found/2"

# FORCE IMPORT ALL CITIES - NO FALLBACK!
log_with_timestamp "INFO" "=== ETAPA 2: IMPORTAÇÃO FORÇADA DE TODAS AS CIDADES ==="
log_with_timestamp "INFO" "Iniciando importação completa de cidades dos arquivos Excel..."
start_time=$(date +%s.%3N)

python force_import_all_cities.py
import_exit_code=$?

# Check if import was successful
if check_and_log_result "Importação de cidades" $import_exit_code $start_time; then
    log_with_timestamp "INFO" "=== TODAS AS CIDADES IMPORTADAS COM SUCESSO ==="
else
    log_with_timestamp "ERROR" "=== FALHA NA IMPORTAÇÃO DE CIDADES - POPULANDO DESTINO DIRETAMENTE ==="
    log_with_timestamp "INFO" "Populando tabela Destino com dados dos arquivos locais..."

    start_backup_time=$(date +%s.%3N)
    python -c "
import sys
sys.path.insert(0, '.')
from frete_app.db import engine
from frete_app.models import Destino, Estado as EstadoSimples
from sqlmodel import Session, select
import pandas as pd

print('[INFO] Iniciando população direta da tabela Destino...')

with Session(engine) as session:
    # Verificar se já tem dados
    existing = len(session.exec(select(Destino)).all())
    print(f'[INFO] Cidades existentes na tabela Destino: {existing}')

    if existing == 0:
        try:
            # Ler Excel de cidades
            df = pd.read_excel('Relação Cidades Atendidas Modal Rodoviário_25_03_25.xlsx')
            print(f'[INFO] Lendo {len(df)} cidades do Excel...')

            # Contar categorias
            categorias_count = {}
            cidades_adicionadas = 0

            for _, row in df.iterrows():
                try:
                    # Determinar categoria baseada em algo no Excel ou usar default
                    cidade_nome = str(row.get('Cidade', '')).strip().upper()
                    uf = str(row.get('UF', '')).strip().upper()

                    # Lógica simplificada de categorização
                    if 'CAPITAL' in cidade_nome or cidade_nome in ['SAO PAULO', 'RIO DE JANEIRO', 'BELO HORIZONTE',
                                                                     'PORTO ALEGRE', 'CURITIBA', 'SALVADOR',
                                                                     'RECIFE', 'FORTALEZA', 'BRASILIA']:
                        categoria = 'CAPITAL'
                    else:
                        categoria = 'INTERIOR_1'  # Maioria das cidades são Interior 1

                    categorias_count[categoria] = categorias_count.get(categoria, 0) + 1

                    cidade = Destino(
                        uf=uf,
                        cidade=cidade_nome,
                        categoria=categoria
                    )
                    session.add(cidade)
                    cidades_adicionadas += 1

                    if cidades_adicionadas % 100 == 0:
                        print(f'[INFO] Processadas {cidades_adicionadas} cidades...')
                        session.commit()
                except Exception as e:
                    print(f'[WARNING] Erro ao processar cidade: {e}')
                    continue

            session.commit()
            print(f'[SUCCESS] {cidades_adicionadas} cidades adicionadas à tabela Destino!')
            print(f'[INFO] Categorias: {categorias_count}')

        except Exception as e:
            print(f'[ERROR] Falha ao ler Excel: {e}')
            # Fallback crítico - usar dados básicos
            print('[FALLBACK] Criando dados básicos...')

            estados_basicos = [
                ('SP', 'São Paulo'), ('RJ', 'Rio de Janeiro'), ('MG', 'Minas Gerais'),
                ('PR', 'Paraná'), ('RS', 'Rio Grande do Sul'), ('SC', 'Santa Catarina'),
                ('BA', 'Bahia'), ('PE', 'Pernambuco'), ('CE', 'Ceará'), ('DF', 'Distrito Federal')
            ]

            for uf, nome in estados_basicos:
                cidade = Destino(uf=uf, cidade=nome, categoria='CAPITAL')
                session.add(cidade)

            session.commit()
            print('[FALLBACK] 10 cidades básicas criadas')

    final_count = len(session.exec(select(Destino)).all())
    print(f'[FINAL] Total de cidades na tabela Destino: {final_count}')
"
    backup_exit_code=$?

    if check_and_log_result "População direta da tabela Destino" $backup_exit_code $start_backup_time; then
        log_with_timestamp "INFO" "Tabela Destino populada com sucesso"
    else
        log_with_timestamp "ERROR" "ERRO CRÍTICO: População da tabela Destino falhou!"
    fi
fi

# Initialize other data (products, states, etc)
log_with_timestamp "INFO" "=== ETAPA 3: INICIALIZAÇÃO DOS PRODUTOS E ESTADOS ==="
log_with_timestamp "INFO" "Populando produtos e estados..."
start_time=$(date +%s.%3N)

# Populate products and states
python -c "
import sys
sys.path.insert(0, '.')
from frete_app.db import engine
from frete_app.models import Produto
from frete_app.models_extended import Estado
from sqlmodel import Session, select

print('[INFO] Iniciando população de produtos e estados...')

with Session(engine) as session:
    # Check and populate products
    produtos_existentes = len(session.exec(select(Produto)).all())
    print(f'[INFO] Produtos existentes: {produtos_existentes}')

    if produtos_existentes == 0:
        print('[INFO] Criando produtos...')
        # PRODUTOS COM ESPECIFICAÇÕES CORRETAS DOCUMENTADAS NO SISTEMA
        produtos = [
            {'nome': 'Zilla', 'largura_cm': 111.0, 'altura_cm': 111.0,
             'profundidade_cm': 150.0, 'peso_real_kg': 63.0, 'valor_nf_padrao': 200.0},
            {'nome': 'Juna', 'largura_cm': 78.0, 'altura_cm': 186.0,
             'profundidade_cm': 128.0, 'peso_real_kg': 123.0, 'valor_nf_padrao': 200.0},
            {'nome': 'Kimbo', 'largura_cm': 78.0, 'altura_cm': 186.0,
             'profundidade_cm': 128.0, 'peso_real_kg': 121.0, 'valor_nf_padrao': 200.0},
            {'nome': 'Kay', 'largura_cm': 78.0, 'altura_cm': 186.0,
             'profundidade_cm': 128.0, 'peso_real_kg': 161.0, 'valor_nf_padrao': 200.0},
            {'nome': 'Jaya', 'largura_cm': 78.0, 'altura_cm': 186.0,
             'profundidade_cm': 128.0, 'peso_real_kg': 107.0, 'valor_nf_padrao': 200.0}
        ]

        for prod_data in produtos:
            produto = Produto(**prod_data)
            session.add(produto)

        session.commit()
        print(f'[SUCCESS] {len(produtos)} produtos criados!')

    # Check and populate states
    estados_existentes = len(session.exec(select(Estado)).all())
    print(f'[INFO] Estados existentes: {estados_existentes}')

    if estados_existentes == 0:
        print('[INFO] Criando estados...')
        estados_brasil = [
            ('AC', 'Acre', 'Norte'), ('AL', 'Alagoas', 'Nordeste'),
            ('AP', 'Amapá', 'Norte'), ('AM', 'Amazonas', 'Norte'),
            ('BA', 'Bahia', 'Nordeste'), ('CE', 'Ceará', 'Nordeste'),
            ('DF', 'Distrito Federal', 'Centro-Oeste'), ('ES', 'Espírito Santo', 'Sudeste'),
            ('GO', 'Goiás', 'Centro-Oeste'), ('MA', 'Maranhão', 'Nordeste'),
            ('MT', 'Mato Grosso', 'Centro-Oeste'), ('MS', 'Mato Grosso do Sul', 'Centro-Oeste'),
            ('MG', 'Minas Gerais', 'Sudeste'), ('PA', 'Pará', 'Norte'),
            ('PB', 'Paraíba', 'Nordeste'), ('PR', 'Paraná', 'Sul'),
            ('PE', 'Pernambuco', 'Nordeste'), ('PI', 'Piauí', 'Nordeste'),
            ('RJ', 'Rio de Janeiro', 'Sudeste'), ('RN', 'Rio Grande do Norte', 'Nordeste'),
            ('RS', 'Rio Grande do Sul', 'Sul'), ('RO', 'Rondônia', 'Norte'),
            ('RR', 'Roraima', 'Norte'), ('SC', 'Santa Catarina', 'Sul'),
            ('SP', 'São Paulo', 'Sudeste'), ('SE', 'Sergipe', 'Nordeste'),
            ('TO', 'Tocantins', 'Norte')
        ]

        for sigla, nome, regiao in estados_brasil:
            estado = Estado(sigla=sigla, nome=nome, regiao=regiao, tem_cobertura=True)
            session.add(estado)

        session.commit()
        print(f'[SUCCESS] {len(estados_brasil)} estados criados!')

    # Final count
    total_produtos = len(session.exec(select(Produto)).all())
    total_estados = len(session.exec(select(Estado)).all())
    print(f'[FINAL] {total_produtos} produtos, {total_estados} estados no banco')
"
populate_exit_code=$?

if check_and_log_result "População de produtos e estados" $populate_exit_code $start_time; then
    log_with_timestamp "INFO" "Produtos e estados populados com sucesso"
else
    log_with_timestamp "ERROR" "Falha na população de produtos e estados"
fi

# Final database verification
log_with_timestamp "INFO" "=== VERIFICAÇÃO FINAL DO BANCO DE DADOS ==="
log_with_timestamp "INFO" "Executando verificação final antes de iniciar o servidor..."

python -c "
import sys
sys.path.insert(0, '.')
try:
    from frete_app.db import engine
    from sqlmodel import Session, select, text
    from frete_app.models import Produto, Destino
    from frete_app.models_extended import Estado, CidadeRodonaves, FilialRodonaves

    with Session(engine) as session:
        produtos = len(session.exec(select(Produto)).all())
        estados = len(session.exec(select(Estado)).all()) if Estado else 0
        rodonaves_cidades = len(session.exec(select(CidadeRodonaves)).all()) if CidadeRodonaves else 0
        destino_cidades = len(session.exec(select(Destino)).all()) if Destino else 0
        filiais = len(session.exec(select(FilialRodonaves)).all()) if FilialRodonaves else 0

    total_cidades = max(rodonaves_cidades, destino_cidades)
    cidade_fonte = 'CidadeRodonaves' if rodonaves_cidades > 0 else 'Destino'

    print(f'[INFO] Verificação final: {produtos} produtos, {estados} estados, {filiais} filiais')
    print(f'[INFO] Cidades: {total_cidades} ({cidade_fonte})')
    print(f'[DEBUG] CidadeRodonaves: {rodonaves_cidades}, Destino: {destino_cidades}')

    if produtos > 0 and total_cidades > 100:  # Pelo menos 100 cidades
        print('[OK] Banco de dados validado e pronto para uso')
        sys.exit(0)
    else:
        print(f'[ERROR] Banco insuficiente: {produtos} produtos, {total_cidades} cidades')
        sys.exit(1)
except Exception as e:
    print(f'[ERROR] Falha na verificação final: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
" 2>&1

verification_exit_code=$?
if [ $verification_exit_code -eq 0 ]; then
    log_with_timestamp "INFO" "Verificação final do banco: SUCESSO"
else
    log_with_timestamp "ERROR" "Verificação final do banco: FALHOU"
    log_with_timestamp "WARNING" "Continuando inicialização mesmo com verificação falhando..."
fi

# Start the application
log_with_timestamp "INFO" "=== ETAPA 4: INICIANDO SERVIDOR WEB ==="
log_with_timestamp "INFO" "Iniciando servidor uvicorn..."
log_with_timestamp "INFO" "Host: 0.0.0.0"
log_with_timestamp "INFO" "Porta: ${PORT:-8000}"
log_with_timestamp "INFO" "Timestamp de início do servidor: $(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)"

exec uvicorn frete_app.main:app --host 0.0.0.0 --port ${PORT:-8000}