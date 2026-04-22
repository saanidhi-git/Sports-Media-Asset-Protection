from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import assets, scrape, pipeline, review, notice, login, users

app = FastAPI(title="SHIELD_MEDIA Backend API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers directly (Frontend proxy will map /api/users -> /users)
app.include_router(login.router)
app.include_router(users.router)
app.include_router(assets.router)
app.include_router(scrape.router)
app.include_router(pipeline.router)
app.include_router(review.router)
app.include_router(notice.router)

@app.get("/")
async def root():
    return {"message": "SHIELD_MEDIA API Online"}
