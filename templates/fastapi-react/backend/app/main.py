"""{{project_name}} — FastAPI application entry point."""
from fastapi import FastAPI

app = FastAPI(title="{{project_name}}")


@app.get("/api/health")
async def health() -> dict[str, str]:
    """Return service health status."""
    return {"status": "ok"}
