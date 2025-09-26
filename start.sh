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
    log_with_timestamp "ERROR" "=== FALHA NA IMPORTAÇÃO DE CIDADES - TENTANDO BACKUP ==="
    log_with_timestamp "INFO" "Iniciando script de backup de inicialização..."

    start_backup_time=$(date +%s.%3N)
    python initialize_db_production.py
    backup_exit_code=$?

    if check_and_log_result "Script de backup de inicialização" $backup_exit_code $start_backup_time; then
        log_with_timestamp "INFO" "Script de backup executado com sucesso"
    else
        log_with_timestamp "ERROR" "ERRO CRÍTICO: Backup de inicialização também falhou!"
    fi
fi

# Initialize other data (products, states, etc)
log_with_timestamp "INFO" "=== ETAPA 3: INICIALIZAÇÃO DOS DADOS RESTANTES ==="
log_with_timestamp "INFO" "Iniciando inicialização de produtos, estados e outros dados..."
start_time=$(date +%s.%3N)

python initialize_database.py
init_exit_code=$?

if check_and_log_result "Inicialização de dados restantes" $init_exit_code $start_time; then
    log_with_timestamp "INFO" "Dados restantes inicializados com sucesso"
else
    log_with_timestamp "ERROR" "Falha na inicialização de dados restantes"
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
    from frete_app.models import Produto
    from frete_app.models_extended import Estado, CidadeRodonaves, FilialRodonaves

    with Session(engine) as session:
        produtos = len(session.exec(select(Produto)).all())
        estados = len(session.exec(select(Estado)).all())
        cidades = len(session.exec(select(CidadeRodonaves)).all())
        filiais = len(session.exec(select(FilialRodonaves)).all())

    print(f'[INFO] Verificação final: {produtos} produtos, {estados} estados, {filiais} filiais, {cidades} cidades')

    if produtos > 0 and estados > 0:
        print('[OK] Banco de dados validado e pronto para uso')
        sys.exit(0)
    else:
        print('[ERROR] Banco de dados não está adequadamente inicializado')
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