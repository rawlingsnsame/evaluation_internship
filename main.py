import logging
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator, model_validator

from src.criterions import SCHOOL_CRITERIONS
from src.validators import ValidationError
from how_to import _HOW_TO
from app import AIResponseError, InternshipEvaluator
 
log = logging.getLogger(__name__)

app = FastAPI(
    title="Internship Evaluation API",
    description="AI-powered internship performance evaluation for COLTECH and NAHPI.",
    version="1.0.0",
)
 

"""Tighten this before production""" 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],    
    allow_methods=["*"],
    allow_headers=["*"],
)

reports: Dict[str, Any] = {}

class PersonalInfo(BaseModel):
    id:   str = Field(..., min_length=1)
    name: str = Field(..., min_length=5)
    school: str = Field(..., pattern="^(COLTECH|NAHPI)$")

class Performance(BaseModel):
    tasks_done:   int   = Field(..., ge=0)
    tasks_total:  int   = Field(..., gt=0)
    days_present: int   = Field(..., ge=0)
    total_days:   int   = Field(..., gt=0)
    average_mark: float = Field(..., ge=0, le=100)
 
    @model_validator(mode="after")
    def check_ratios(self) -> "Performance":
        if self.tasks_done > self.tasks_total:
            raise ValueError(
                f"tasks_done ({self.tasks_done}) cannot exceed tasks_total ({self.tasks_total})"
            )
        if self.days_present > self.total_days:
            raise ValueError(
                f"days_present ({self.days_present}) cannot exceed total_days ({self.total_days})"
            )
        return self
    
class ColtechComments(BaseModel):
    participation:    str = Field(..., min_length=1)
    discipline:       str = Field(..., min_length=1)
    integration:      str = Field(..., min_length=1)
    general_behavior: str = Field(..., min_length=1)

    @field_validator("participation", "discipline", "integration", "general_behavior")
    @classmethod
    def no_blank_comments(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Comment cannot be blank.")
        return v.strip()

class ColtechRemarks(BaseModel):
    supervisor_remark: str = Field(..., min_length=1)
    comments: ColtechComments

class NahpiRemarks(BaseModel):
    supervisor_remark: str = Field(..., min_length=1)
 
class EvaluationRequest(BaseModel):
    personal:    PersonalInfo
    performance: Performance
    remarks:     Dict[str, Any] 

evaluator = InternshipEvaluator()

@app.exception_handler(StarletteHTTPException)
async def catch_all(request: Request, exc: StarletteHTTPException):
    if request.url.path == "/evaluate":
        raise exc   # let /evaluate's own errors pass through normally
    return JSONResponse(status_code=exc.status_code, content=_HOW_TO)

@app.post("/evaluate", status_code=200)
async def evaluate(request: EvaluationRequest):
    """
    Submit intern data for AI evaluation.
    Returns the full scored report.
    """
    # Validate school-specific remarks shape
    school = request.personal.school
    try:
        if school == "COLTECH":
            validated_remarks = ColtechRemarks(**request.remarks)
        elif school == "NAHPI":
            validated_remarks = NahpiRemarks(**request.remarks)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid remarks: {e}")
 
    # Run evaluation
    try:
        report = evaluator.generate_report(
            school=school,
            personal=request.personal.model_dump(),
            performance=request.performance.model_dump(),
            remarks=validated_remarks.model_dump(),
        )
        
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except AIResponseError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        log.exception("Unexpected error during evaluation")
        raise HTTPException(status_code=500, detail="Internal server error.")
 
    # Store and return
    return {"report": report}