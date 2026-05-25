import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import upload, records, review, iot, predictive
from generators.sewer_infrastructure import seed_sewer_infrastructure_if_empty

app = FastAPI(
    title="UrbanFix 311 AI Data Sorting & Organization API",
    description="FastAPI Backend for cleaning, organizing, and quarantining civic complaints.",
    version="1.0.0"
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify front-end domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database seeding startup event
@app.on_event("startup")
async def startup_event():
    seed_sewer_infrastructure_if_empty()

# Register routes
app.include_router(upload.router)
app.include_router(records.router)
app.include_router(review.router)
app.include_router(iot.router)
app.include_router(predictive.router)

@app.get("/")
async def root():
    return {
        "status": "online",
        "service": "UrbanFix 311 Phase 1 API",
        "docs": "/docs"
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
