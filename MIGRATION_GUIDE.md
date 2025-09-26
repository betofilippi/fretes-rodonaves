# Guia de Migração - Sistema Estendido Rodonaves

## Visão Geral
O sistema foi expandido para suportar todas as 4,219 cidades atendidas pela Rodonaves, com cálculo automático de TDA (Taxa Dificuldade Acesso) e TRT (Taxa Restrição Trânsito).

## Novos Arquivos Criados

### 1. Modelos Estendidos (`frete_app/models_extended.py`)
- `Estado`: Estados brasileiros com cobertura
- `FilialRodonaves`: 263 filiais/bases operacionais
- `CidadeRodonaves`: 4,219 cidades com categorização completa
- `TaxaEspecial`: 1,717 taxas TDA/TRT
- `CEPEspecial`: CEPs com regras especiais
- `TabelaTarifaCompleta`: Tarifas por estado+categoria

### 2. Scripts de Importação
- `import_cidades.py`: Importa cidades do Excel oficial
- `import_taxas.py`: Importa TDAs e TRTs

### 3. Cálculo Estendido (`frete_app/calc_extended.py`)
- Suporte completo a TDA/TRT
- Cálculo por cidade específica
- Aplicação de taxas percentuais ou fixas

### 4. Interface Estendida (`frete_app/views_extended.py`)
- Busca de cidades com autocomplete
- Exibição de taxas especiais
- Estatísticas do sistema

## Como Migrar os Dados

### Passo 1: Importar Cidades
```bash
python import_cidades.py "C:\Users\Beto\Dropbox\NXT\Dev\Relação Cidades Atendidas Modal Rodoviário_25_03_25.xlsx"
```

Isso irá:
- Criar 4,219 cidades
- Criar estados e filiais
- Gerar tarifas base por categoria

### Passo 2: Importar Taxas Especiais
```bash
python import_taxas.py "C:\Users\Beto\Dropbox\NXT\Dev\TDAs e TRTs 2025 11_04_25 - NXT.xlsx"
```

Isso irá:
- Importar 1,717 taxas TDA/TRT
- Associar às cidades correspondentes
- Marcar cidades com flags tem_tda/tem_trt

### Passo 3: Reiniciar o Servidor
```bash
python -m uvicorn frete_app.main:app --reload
```

## Novos Endpoints

### Interface Original (10 cidades)
- `http://localhost:8000/` - Interface simplificada

### Interface Estendida (4,219 cidades)
- `http://localhost:8000/extended` - Interface completa com busca
- `http://localhost:8000/extended/stats` - Estatísticas do sistema

## Funcionalidades Novas

### 1. Busca de Cidades
- Selecione o estado primeiro
- Digite pelo menos 2 caracteres
- Autocomplete mostra até 20 sugestões
- Indicadores visuais para TDA/TRT

### 2. Cálculo com Taxas Especiais
- TDA aplicada automaticamente quando presente
- TRT calculada sobre o frete base
- Breakdown detalhado mostrando cada componente

### 3. Categorização Automática
- **CAPITAL**: Capitais estaduais
- **INTERIOR_1**: Regiões metropolitanas e cidades grandes
- **INTERIOR_2**: Demais cidades
- **FLUVIAL**: Acesso fluvial especial

## Estrutura de Taxas

### TDA (Taxa Dificuldade Acesso)
- Aplicada em cidades de difícil acesso
- Pode ser valor fixo (R$) ou percentual (% da NF)
- 1,200+ cidades com TDA

### TRT (Taxa Restrição Trânsito)
- Aplicada em cidades com restrições municipais
- Geralmente valor fixo
- 500+ cidades com TRT

## Exemplo de Uso Programático

```python
from frete_app.calc_extended import calcula_frete_completo

# Calcular frete para São Paulo capital
resultado = calcula_frete_completo(
    produto_id=1,      # Zilla
    cidade_id=1000,    # São Paulo/SP
    valor_nf=2000.00
)

print(f"Frete base: R$ {resultado.base_faixa:.2f}")
print(f"TDA: R$ {resultado.tda:.2f}")
print(f"TRT: R$ {resultado.trt:.2f}")
print(f"Total: R$ {resultado.total:.2f}")
```

## Verificação de Importação

Para verificar se os dados foram importados corretamente:

```python
from sqlmodel import Session, select
from frete_app.db import engine
from frete_app.models_extended import CidadeRodonaves, TaxaEspecial

with Session(engine) as session:
    total_cidades = session.exec(select(CidadeRodonaves)).count()
    total_taxas = session.exec(select(TaxaEspecial)).count()

    print(f"Cidades: {total_cidades}")
    print(f"Taxas: {total_taxas}")
```

## Notas Importantes

1. **Compatibilidade**: O sistema original com 10 cidades continua funcionando
2. **Performance**: Busca de cidades usa índices para rapidez
3. **Precisão**: Categorização pode precisar ajustes manuais para algumas cidades
4. **Taxas**: Valores de TDA/TRT são aplicados automaticamente no cálculo

## Troubleshooting

### Erro: "Cidade não encontrada"
- Verifique se importou as cidades (passo 1)
- Nome da cidade deve corresponder exatamente

### Erro: "Taxa não aplicada"
- Verifique se importou as taxas (passo 2)
- Algumas cidades podem não ter TDA/TRT

### Performance lenta
- Crie índices adicionais se necessário
- Use cache para cidades frequentes

## Próximos Passos

1. Ajustar categorização de cidades específicas
2. Adicionar suporte a CEPs especiais
3. Implementar cache de cálculos frequentes
4. Adicionar API REST para integração