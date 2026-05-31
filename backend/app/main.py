from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import dashboard, outlets, budget, xai, map

app = FastAPI(
    title="Outlet Intelligence API",
    description="Backend API for exploring outlet predictions, spatial features, marketing budget allocations, mapping vectors, and XAI narratives.",
    version="0.1.0"
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Routers
app.include_router(dashboard.router)
app.include_router(outlets.router)
app.include_router(budget.router)
app.include_router(xai.router)
app.include_router(map.router)

@app.get("/")
def read_root():
    return {
        "status": "online",
        "message": "Welcome to the Outlet Intelligence API. Access docs at /docs or /redoc"
    }
