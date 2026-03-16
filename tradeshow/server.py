"""Run the Trade Show Trend Analysis API server."""
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "tradeshow.api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
