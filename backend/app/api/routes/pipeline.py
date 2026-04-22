from fastapi import APIRouter

router = APIRouter(prefix="/pipeline", tags=["Pipeline"])

@router.post("/orchestrate")
async def orchestrate_flow(asset_id: str):
    # Call Orchestrator service to run full flow: Fingerprint -> Match -> Score -> Decision
    return {"status": "processing", "asset_id": asset_id}
