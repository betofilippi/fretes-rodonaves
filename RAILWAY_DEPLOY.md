# 🚂 Deploy no Railway - Calculadora de Frete Rodonaves

## ✅ Arquivos já preparados:
- `requirements.txt` - Dependências Python
- `railway.toml` - Configuração do Railway
- `Procfile` - Comando de start
- `.gitignore` - Arquivos para ignorar

## 🎯 Próximos passos para deploy:

### 1️⃣ **Criar repositório no GitHub**
1. Acesse: https://github.com/new
2. Nome: `fretes-rodonaves`
3. Deixe público ou privado
4. **NÃO** adicione README (já existe)

### 2️⃣ **Push para GitHub**
Execute estes comandos no terminal:
```bash
cd "C:\Users\Beto\Dropbox\NXT\Dev\fretes-rodonaves"
git remote add origin https://github.com/SEU_USUARIO/fretes-rodonaves.git
git branch -M main
git push -u origin main
```

### 3️⃣ **Deploy no Railway**
1. Acesse: https://railway.app
2. Login com GitHub
3. "New Project" → "Deploy from GitHub repo"
4. Selecione `fretes-rodonaves`
5. Deploy automático iniciará

### 4️⃣ **Configurações no Railway**
Adicionar estas variáveis de ambiente no painel:
- `PYTHONPATH` = `.`
- `DATABASE_URL` = `sqlite:///./data/frete.db`

### 5️⃣ **Domínio customizado**
1. Settings → Domains
2. Adicionar: `transportadora.app`
3. Configurar DNS apontando para Railway

## 🎉 Sistema incluí:
- ✅ 4.041 cidades com prazos de entrega CPF
- ✅ Cálculo de frete completo com taxas
- ✅ Interface responsiva
- ✅ 113 cidades fluviais identificadas
- ✅ Sistema pronto para produção

**URL final:** https://transportadora.app