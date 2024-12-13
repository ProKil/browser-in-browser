from main import web_app, startup_event, shutdown_event, state

import modal

app = modal.App("bib_backend")

# Create an image that includes Redis
image = modal.Image.debian_slim().pip_install(["playwright", "fastapi", "uvicorn", "pydantic"]).run_commands(
    "playwright install-deps",
    "playwright install",
)

@app.cls(image=image, cpu=8, concurrency_limit=1, allow_concurrent_inputs=10)
class ModalApp:
    def __init__(self):
        self.app = web_app

    @modal.enter()
    async def startup(self):
        await startup_event()

    @modal.exit()
    async def shutdown(self):
        await shutdown_event()

    @modal.asgi_app()
    def serve(self):
        return self.app


