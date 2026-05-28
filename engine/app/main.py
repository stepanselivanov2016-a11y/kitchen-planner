from fastapi import FastAPI
from app.auth import history_router, router as auth_router
from app.database import Base, engine
from app.llm_preferences import router as preferences_router
from app.models import GenerateRequest, GenerateResponse
from app.prompt_parser import parse_prompt
from app.generator import generate_layout
from app.renderer import render_top_view, render_front_view, render_side_view

app = FastAPI(title="Kitchen Planner Engine")
app.include_router(auth_router)
app.include_router(history_router)
app.include_router(preferences_router)


@app.on_event("startup")
def create_database_tables():
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest):
    normalized_spec = parse_prompt(req.prompt or "")
    module_options = req.module_options or {}

    generated_layout = generate_layout(
        normalized_spec=normalized_spec,
        module_options=module_options,
    )

    top_view_svg = render_top_view(generated_layout)
    front_view_svg = render_front_view(generated_layout)
    side_view_svg = render_side_view(generated_layout)

    return GenerateResponse(
        normalized_spec=normalized_spec,
        module_options=module_options,
        generated_layout=generated_layout,
        top_view_svg=top_view_svg,
        front_view_svg=front_view_svg,
        side_view_svg=side_view_svg,
    )
