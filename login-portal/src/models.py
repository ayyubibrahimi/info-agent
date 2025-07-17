from typing import Dict, List
from pydantic import BaseModel, Field

class ScreenshotAnalysis(BaseModel):
    page_type: str = Field(description="Type of page: 'portal_home', 'login_form', 'logged_in_dashboard', 'error', 'other'")
    login_required: bool = Field(description="Whether login is required to proceed")
    login_elements_found: Dict[str, bool] = Field(
        default={
            "username_field": False,
            "password_field": False, 
            "submit_button": False,
            "sign_in_link": False
        },
        description="Login elements present: username_field, password_field, submit_button, sign_in_link"
    )
    key_elements: List[str] = Field(description="Important elements visible on the page")
    next_steps: List[str] = Field(description="Recommended actions to take next")
    confidence: float = Field(description="Confidence in analysis (0-1)")

class LoginCredentials(BaseModel):
    username: str
    password: str
