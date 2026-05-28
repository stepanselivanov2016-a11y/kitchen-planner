from pydantic import BaseModel
from typing import Any, Dict, Optional


class GenerateRequest(BaseModel):
    prompt: str = ""
    module_options: Optional[Dict[str, Any]] = None


class GenerateResponse(BaseModel):
    normalized_spec: Dict[str, Any]
    module_options: Dict[str, Any]
    generated_layout: Dict[str, Any]
    top_view_svg: str
    front_view_svg: str
    side_view_svg: str = ""
