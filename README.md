# Frete Rodonaves App — FastAPI + HTMX

Sistema de cálculo de fretes Rodonaves com **FastAPI**, **HTMX** e estilo **FastHTML** para componentes HTML em Python.

## Características

- ✅ **Cálculo preciso de fretes** com cubagem, faixas de peso, excedente, pedágio, F-valor, GRIS e ICMS
- ✅ **Produtos cadastráveis** com dimensões e peso
- ✅ **Versões de tabela** com histórico e ativação
- ✅ **Upload de PDF** para extração automática de tarifas
- ✅ **Corredor KM** com fator multiplicador F
- ✅ **Interface HTMX** sem recarregamento de página
- ✅ **Componentes HTML em Python** (estilo FastHTML)

## Estrutura do Projeto

```
frete_app/
├── main.py              # FastAPI app
├── models.py            # SQLModel (produtos, tarifas, versões)
├── calc.py              # Motor de cálculo 100% parametrizado
├── parsers.py           # Extração de PDF (Camelot + pdfplumber)
├── views.py             # Endpoints FastAPI + HTMX
├── fasthtml.py          # Helpers HTML declarativos
├── db.py                # Sessão SQLite/Postgres
├── seed_data.py         # Dados iniciais
├── static/
│   ├── htmx.min.js     # HTMX library
│   └── styles.css      # CSS responsivo
└── data/uploads/       # PDFs enviados
```

## Instalação

### 1. Instalar dependências

```bash
# Com Poetry (recomendado)
poetry install

# Ou com pip
pip install fastapi uvicorn sqlmodel jinja2 pdfplumber camelot-py python-multipart pydantic
```

### 2. Instalar Ghostscript (para Camelot)

**Windows:**
- Baixar de https://ghostscript.com/download/gsdnld.html
- Instalar e adicionar ao PATH

**Linux:**
```bash
sudo apt-get install ghostscript
```

**macOS:**
```bash
brew install ghostscript
```

### 3. Executar aplicação

```bash
# Com Poetry
poetry run python -m frete_app.main

# Ou diretamente
cd frete_app
python main.py

# Ou com uvicorn
uvicorn frete_app.main:app --reload
```

Acesse: http://localhost:8000

## Funcionalidades

### 1. Calculadora de Frete (Página Principal)

- Selecionar produto cadastrado
- Escolher destino (UF/cidade/categoria)
- Informar valor da Nota Fiscal
- **Cálculo automático** com breakdown detalhado:
  - Peso cubado vs real
  - Faixa base + excedente
  - Pedágio por fração de 100kg
  - F-valor (0,5% do valor NF, mín R$ 4,78)
  - GRIS (0,1% até R$ 10k, 0,23% acima, mín R$ 1,10)
  - ICMS (12%)

### 2. Gestão de Produtos

- CRUD completo via HTMX
- Dimensões (L×A×P em cm)
- Peso real em kg
- Valor NF padrão

### 3. Versões de Tabela

- **Upload de PDF** da Rodonaves
- **Extração automática** de tarifas e parâmetros
- **Histórico de versões** com ativação
- Cada versão mantém suas próprias tarifas e parâmetros

### 4. Corredor KM (Planejado)

- Upload de CT-e para extrair fator F
- Mapeamento destino → corredor
- Multiplicação da base por fator F

## Arquitetura

### Motor de Cálculo (`calc.py`)

Totalmente parametrizado por versão:

```python
resultado = calcula_frete(
    inp=CalcInput(...),      # Dados do produto/envio
    tarifa=Tarifa(...),      # Faixas por categoria destino
    params=ParamSet(...)     # Parâmetros gerais da versão
)
```

### Parsing de PDF (`parsers.py`)

- **Camelot**: extração de tabelas estruturadas
- **pdfplumber**: extração de texto para parâmetros gerais
- **Regex patterns**: identificação de valores e categorias

### Interface HTMX (`views.py` + `fasthtml.py`)

- **Server-side rendering** com componentes Python
- **Partial updates** via `hx-get`/`hx-post`
- **Zero JavaScript** customizado necessário

## Produtos Pré-cadastrados

Com base no `especificacoes_produtos.md`:

| Produto | Dimensões (cm) | Peso (kg) | Valor NF |
|---------|----------------|-----------|----------|
| Zilla   | 72×53×130      | 50        | R$ 149   |
| Juna    | 78×186×128     | 123       | R$ 200   |
| Kimbo   | 78×186×128     | 121       | R$ 200   |
| Kay     | 78×186×128     | 161       | R$ 200   |
| Jaya    | 78×186×128     | 107       | R$ 200   |

## Dados de Exemplo

O sistema vem com:
- **10 destinos** (SP, RJ, MG, PR, SC, RS)
- **Tarifas por categoria** com valores aproximados
- **Parâmetros gerais** padrão da Rodonaves
- **1 versão ativa** para demonstração

## Configuração do Banco

Por padrão usa **SQLite** (`frete.db`). Para PostgreSQL, alterar em `db.py`:

```python
DATABASE_URL = "postgresql://user:password@localhost/dbname"
```

## API Endpoints

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET    | `/`                    | Página principal (calculadora) |
| POST   | `/cotacao`             | Calcular frete (HTMX) |
| GET    | `/produtos`            | Listar produtos |
| POST   | `/produtos`            | Criar produto |
| GET    | `/versoes`             | Listar versões de tabela |
| POST   | `/versoes/upload`      | Upload PDF + parsing |
| GET    | `/health`              | Health check |

## Exemplo de Uso

1. **Cálculo simples:**
   - Produto: Juna (78×186×128cm, 123kg)
   - Destino: São Paulo/SP (SP_CAPITAL)
   - Valor NF: R$ 1.500,00
   - **Resultado:** peso taxável 192kg, base R$ 120, total ~R$ 180

2. **Upload de tabela:**
   - Fazer upload do PDF oficial da Rodonaves
   - Sistema extrai automaticamente faixas e parâmetros
   - Ativar nova versão
   - Cálculos passam a usar novos valores

## Próximos Passos

- [ ] CRUD de destinos/categorias
- [ ] Upload e parsing de CT-e para corredores
- [ ] Mapeamento destino → corredor KM
- [ ] Relatórios e histórico de cotações
- [ ] API REST para integração externa
- [ ] Autenticação/autorização
- [ ] Deploy com Docker

## Desenvolvimento

```bash
# Instalar dependências de desenvolvimento
poetry install --with dev

# Formatar código
poetry run black frete_app/

# Executar testes (quando implementados)
poetry run pytest
```

## Suporte

Sistema desenvolvido seguindo especificações detalhadas para cálculo preciso de fretes Rodonaves, incluindo todas as taxas e impostos aplicáveis.

Para dúvidas sobre implementação ou extensões, consulte o código-fonte comentado ou a documentação das bibliotecas utilizadas.