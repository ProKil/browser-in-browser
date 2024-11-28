from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel
from playwright.async_api import async_playwright, Browser, Page, BrowserContext, Playwright
from typing import AsyncGenerator, Optional, Dict, Any, Union, Set
import asyncio
import logging
from dataclasses import dataclass
import uvicorn
import json
import logging

# import modal

# Type aliases
JsonResponse = Dict[str, Any]
BinaryResponse = bytes

# Pydantic models with proper typing
class ClickPayload(BaseModel):
    x: float
    y: float

    class Config:
        frozen = True

class ScrollPayload(BaseModel):
    dx: float
    dy: float

    class Config:
        frozen = True

class KeyboardPayload(BaseModel):
    key: str

    class Config:
        frozen = True

class GotoPayload(BaseModel):
    url: str

    class Config:
        frozen = True

# web_application state container
@dataclass
class web_appState:
    playwright: Optional[Playwright] = None
    browser: Optional[Browser] = None
    context: Optional[BrowserContext] = None
    page: Optional[Page] = None
    active_connections: Set[WebSocket] = None

    def __post_init__(self):
        self.active_connections = set()

web_app = FastAPI()
# app = modal.App("browser-backend")
# image = modal.Image.debian_slim().pip_install(
#     ["playwright", "uvicorn"]
# ).run_commands(
#     "playwright install --with-deps"
# )
state = web_appState()

# Add CORS middleware
web_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def init_browser() -> None:
    """Initialize browser and related objects."""
    state.playwright = await async_playwright().start()
    if state.playwright is None:
        raise RuntimeError("Failed to start playwright")
    
    state.browser = await state.playwright.chromium.launch(
        headless=True,
        args=['--no-sandbox', '--disable-setuid-sandbox']
    )
    
    if state.browser is None:
        raise RuntimeError("Failed to launch browser")
    
    state.context = await state.browser.new_context(
        viewport={'width': 1280, 'height': 800},
        ignore_https_errors=True
    )
    
    if state.context is None:
        raise RuntimeError("Failed to create browser context")
    
    state.page = await state.context.new_page()
    if state.page is None:
        raise RuntimeError("Failed to create page")
    
    await state.page.goto('about:blank')

@web_app.on_event("startup")
async def startup_event() -> None:
    await init_browser()

@web_app.on_event("shutdown")
async def shutdown_event() -> None:
    if state.context:
        await state.context.close()
    if state.browser:
        await state.browser.close()
    if state.playwright:
        await state.playwright.stop()

async def screenshot_loop(websocket: WebSocket) -> None:
    """Generate and send screenshots over WebSocket."""
    if not state.page:
        raise RuntimeError("Page not initialized")
    
    try:
        while True:
            if websocket not in state.active_connections:
                break
                
            screenshot: bytes = await state.page.screenshot(
                type='jpeg',
                quality=70
            )
            await websocket.send_bytes(screenshot)
            await asyncio.sleep(0.03)  # 10 FPS
            
    except Exception as e:
        logging.error(f"Screenshot error: {str(e)}")
        if websocket in state.active_connections:
            state.active_connections.remove(websocket)

@web_app.websocket("/screenshot")
async def websocket_screenshot(websocket: WebSocket) -> None:
    """WebSocket endpoint for screenshot streaming."""
    await websocket.accept()
    state.active_connections.add(websocket)
    
    try:
        await screenshot_loop(websocket)
    except WebSocketDisconnect:
        state.active_connections.remove(websocket)
    except Exception as e:
        logging.error(f"WebSocket error: {str(e)}")
        if websocket in state.active_connections:
            state.active_connections.remove(websocket)

# Rest of the endpoints remain the same...
# (click, scroll, keyboard, goto, pdf, content, title, health)
    
@web_app.post("/hover")
async def hover_coordinate(payload: ClickPayload) -> JsonResponse:
    """Hover at specified coordinates."""
    if not state.page:
        raise HTTPException(status_code=500, detail="Page not initialized")
    
    try:
        await state.page.mouse.move(payload.x * 1280, payload.y * 800)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@web_app.post("/scroll")
async def scroll_page(payload: ScrollPayload) -> JsonResponse:
    """Scroll the page by specified deltas."""
    if not state.page:
        raise HTTPException(status_code=500, detail="Page not initialized")
    
    try:
        await state.page.evaluate(f"window.scrollBy({payload.dx * 1280}, {payload.dy * 800})")
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@web_app.post("/click")
async def click_coordinate(payload: ClickPayload) -> JsonResponse:
    """Click at specified coordinates and focus element if clickable."""
    if not state.page:
        raise HTTPException(status_code=500, detail="Page not initialized")
    
    try:
        # Click the coordinate
        await state.page.mouse.click(payload.x * 1280, payload.y * 800)

        element = await state.page.evaluate("""
            (x, y) => {
                const element = document.elementFromPoint(x, y);
                if (element) {
                    element.focus();
                    return true;
                }
                return false;
            }
        """, payload.x * 1280, payload.y * 800)
        
        return {
            "success": True,
            "focused": element
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@web_app.post("/keyboard")
async def type_keys(payload: KeyboardPayload) -> JsonResponse:
    """Type specified keys into the focused element."""
    if not state.page:
        raise HTTPException(status_code=500, detail="Page not initialized")
    
    try:
        # Check if there's a focused input element
        has_focused = await state.page.evaluate("""
            () => {
                const active = document.activeElement;
                return active && (
                    active.tagName === 'INPUT' || 
                    active.tagName === 'TEXTAREA' || 
                    active.contentEditable === 'true'
                );
            }
        """)

        logging.info(f"Focused element: {has_focused}")
        
        if not has_focused:
            return {
                "success": False,
                "error": "No input element is focused"
            }
            
        # Type the keys
        await state.page.keyboard.press(payload.key)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@web_app.post("/goto")
async def goto_url(payload: GotoPayload) -> JsonResponse:
    """Navigate to specified URL."""
    if not state.page:
        raise HTTPException(status_code=500, detail="Page not initialized")
    
    try:
        await state.page.goto(payload.url, wait_until='networkidle')
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@web_app.post("/back")
async def go_back() -> JsonResponse:
    """Navigate back in browser history."""
    if not state.page:
        raise HTTPException(status_code=500, detail="Page not initialized")
    
    try:
        # Check if we can go back
        can_go_back = await state.page.evaluate("window.history.length > 1")
        
        if not can_go_back:
            return {
                "success": False,
                "error": "No previous page in history"
            }
            
        await state.page.go_back(wait_until='networkidle')
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@web_app.post("/forward")
async def go_forward() -> JsonResponse:
    """Navigate forward in browser history."""
    if not state.page:
        raise HTTPException(status_code=500, detail="Page not initialized")
    
    try:
        # Check if we can go forward
        can_go_forward = await state.page.evaluate("""
            () => {
                const current = window.history.state;
                return window.history.forward(), window.history.state !== current;
            }
        """)
        
        if not can_go_forward:
            return {
                "success": False,
                "error": "No next page in history"
            }
            
        await state.page.go_forward(wait_until='networkidle')
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
# @app.function(image=image)
# @modal.asgi_app()
# def fastapi_web_app() -> FastAPI:
#     return web_app

def start_server(port: int) -> None:
    """Start the FastAPI server."""
    uvicorn.run("main:web_app", host="0.0.0.0", port=port, reload=True)

if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    start_server(port)