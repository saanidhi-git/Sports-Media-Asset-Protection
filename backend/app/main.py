from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import assets, scrape, pipeline, review, notice

app = FastAPI(title="SHIELD_MEDIA Backend API")

# Add CORS middleware to allow the Angular frontend on port 4200
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(assets.router)
app.include_router(scrape.router)
app.include_router(pipeline.router)
app.include_router(review.router)
app.include_router(notice.router)

@app.get("/")
async def root():
    return {"message": "Hello from SHIELD_MEDIA Backend"}
