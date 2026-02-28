"""Application instance for uvicorn.

Entry point: uvicorn shelf_mind.webapp.app:app
"""

from shelf_mind.webapp.main import create_app

# Create application instance
app = create_app()

if __name__ == "__main__":
    import uvicorn

    from shelf_mind.params.shelf_mind_params import get_webapp_params

    params = get_webapp_params()
    uvicorn.run(
        "shelf_mind.webapp.app:app",
        host=params.host,
        port=params.port,
        reload=params.debug,
    )
