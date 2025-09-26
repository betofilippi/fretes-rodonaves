from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from .db import create_db_and_tables
from .views import router as ui_router
from .views_extended import router as extended_router
from .seed_data import seed_initial_data

app = FastAPI(
    title="Calculadora de Frete Rodonaves",
    description="Sistema de cálculo de fretes com FastAPI e HTMX",
    version="1.0.0"
)

# CORS middleware (se necessário para desenvolvimento)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, especificar domínios
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Servir arquivos estáticos
import os
try:
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    if os.path.exists(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")
except Exception as e:
    print(f"Warning: Could not mount static files: {e}")

# Rota raiz redireciona para /extended (sistema principal)
@app.get("/")
async def root():
    """Redireciona para o sistema principal /extended"""
    return RedirectResponse(url="/extended", status_code=307)

# Comentado - sistema antigo não é mais necessário
# app.include_router(ui_router)

# Sistema principal - extended
app.include_router(extended_router)


@app.on_event("startup")
async def startup_event():
    """Inicialização da aplicação"""
    try:
        # Criar tabelas
        create_db_and_tables()
        print("Database tables created successfully")

        # Popular dados iniciais se necessário
        # Agora seed_initial_data() tem os produtos de frete corretos
        seed_initial_data()
        print("Initial data seeded successfully")
    except Exception as e:
        print(f"Warning: Startup initialization failed: {e}")
        # Continue execution even if database setup fails


@app.get("/health")
async def health_check():
    """Endpoint de health check"""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "frete_app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )