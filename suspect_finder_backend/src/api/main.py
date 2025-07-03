"""
Suspect Finder Backend API

Provides RESTful endpoints for managing cases, suspects, clues, twists, and solutions,
with business logic for contradictions, twists, and solution validation.

Features:
- CRUD endpoints for all entities.
- Game logic endpoints for highlighting contradictions/twists and validating solutions.
- Uses SQLAlchemy ORM models from suspect_finder_database.
- CORS enabled for all origins.
- OpenAPI docs with tags, parameter details, and example responses.

To run: uvicorn src.api.main:app --reload
"""

import sys
import os

# Ensure suspect_finder_database is importable
backend_root = os.path.dirname(os.path.abspath(__file__))
db_root = os.path.abspath(os.path.join(backend_root, "../../../suspect_finder_database"))
sys.path.append(db_root)

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict

from suspect_finder_database.db import get_db
from suspect_finder_database.models import Case, Suspect, Clue, Twist, Solution

from sqlalchemy.orm import Session

# App-level OpenAPI metadata
app = FastAPI(
    title="Suspect Finder Backend API",
    description="API for managing fictional crime mystery cases, suspects, clues, contradictions, and solutions. Provides interactive endpoints for game features.",
    version="1.0.0",
    openapi_tags=[
        {"name": "Cases", "description": "Operations on mystery cases"},
        {"name": "Suspects", "description": "CRUD and query suspects in cases"},
        {"name": "Clues", "description": "CRUD and query clues belonging to cases"},
        {"name": "Twists", "description": "Handle case twists/contradictions"},
        {"name": "Solutions", "description": "Solution and solution validation endpoints"},
        {"name": "Gameplay", "description": "Logic endpoints: contradictions, twists, solution validation"},
        {"name": "Utility", "description": "Basic utility endpoints"}
    ]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#
# ---- Pydantic Schemas ----
#
class SuspectBase(BaseModel):
    name: str = Field(..., description="Suspect's name")
    description: str = Field(..., description="Description or background")
    attributes: Optional[dict] = Field(None, description="Extra attributes (e.g. motive, personality)")

class SuspectCreate(SuspectBase):
    pass

class SuspectRead(SuspectBase):
    id: int
    case_id: int

    class Config:
        orm_mode = True

class ClueBase(BaseModel):
    clue_type: str = Field(..., description="Type of clue: physical, alibi, etc.")
    description: str = Field(..., description="Clue description")

class ClueCreate(ClueBase):
    pass

class ClueRead(ClueBase):
    id: int
    case_id: int

    class Config:
        orm_mode = True

class TwistBase(BaseModel):
    description: str = Field(..., description="Description of twist or contradiction")

class TwistCreate(TwistBase):
    pass

class TwistRead(TwistBase):
    id: int
    case_id: int

    class Config:
        orm_mode = True

class SolutionBase(BaseModel):
    summary: str = Field(..., description="Summary (high level answer)")
    how_solved: Optional[str] = Field(None, description="How the mystery was solved")

class SolutionCreate(SolutionBase):
    pass

class SolutionRead(SolutionBase):
    id: int
    case_id: int

    class Config:
        orm_mode = True

class CaseBase(BaseModel):
    title: str = Field(..., description="Case title")
    description: str = Field(..., description="Briefing/overview")
    crime_scene: str = Field(..., description="Text of the crime scene")

class CaseCreate(CaseBase):
    suspects: Optional[List[SuspectCreate]] = Field(default_factory=list, description="List of suspects")
    clues: Optional[List[ClueCreate]] = Field(default_factory=list, description="List of clues")
    twists: Optional[List[TwistCreate]] = Field(default_factory=list, description="List of twists")
    solution: Optional[SolutionCreate] = Field(None, description="Solution to the case")

class CaseRead(CaseBase):
    id: int
    suspects: List[SuspectRead] = []
    clues: List[ClueRead] = []
    twists: List[TwistRead] = []
    solution: Optional[SolutionRead]

    class Config:
        orm_mode = True

#
# ---- Utility / Health ----
#
# PUBLIC_INTERFACE
@app.get("/", response_model=dict, tags=["Utility"])
def health_check():
    """Health check endpoint."""
    return {"message": "Healthy"}

#
# ---- CRUD for Cases ----
#
# PUBLIC_INTERFACE
@app.post("/cases", response_model=CaseRead, status_code=201, summary="Create new case", tags=["Cases"])
def create_case(case: CaseCreate, db: Session = Depends(get_db)):
    """
    Create a new mystery case with optional suspects, clues, twists, and solution.
    """
    db_case = Case(
        title=case.title, description=case.description, crime_scene=case.crime_scene
    )
    db.add(db_case)
    db.flush()  # To assign ID for FK
    # Add nested entities
    for suspect in case.suspects:
        db_suspect = Suspect(
            name=suspect.name,
            description=suspect.description,
            attributes=suspect.attributes,
            case_id=db_case.id,
        )
        db.add(db_suspect)
    for clue in case.clues:
        db_clue = Clue(
            clue_type=clue.clue_type,
            description=clue.description,
            case_id=db_case.id,
        )
        db.add(db_clue)
    for twist in case.twists:
        db_twist = Twist(
            description=twist.description,
            case_id=db_case.id,
        )
        db.add(db_twist)
    if case.solution:
        db_solution = Solution(
            summary=case.solution.summary,
            how_solved=case.solution.how_solved,
            case_id=db_case.id,
        )
        db.add(db_solution)
    db.commit()
    db.refresh(db_case)
    # Force relationships to refresh
    return db_case

# PUBLIC_INTERFACE
@app.get("/cases", response_model=List[CaseRead], summary="List all cases", tags=["Cases"])
def list_cases(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    """
    List all mystery cases.
    """
    cases = db.query(Case).offset(skip).limit(limit).all()
    return cases

# PUBLIC_INTERFACE
@app.get("/cases/{case_id}", response_model=CaseRead, summary="Get case by ID", tags=["Cases"])
def get_case(case_id: int, db: Session = Depends(get_db)):
    """
    Get case details by ID (including suspects, clues, twists, and solution).
    """
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case

# PUBLIC_INTERFACE
@app.put("/cases/{case_id}", response_model=CaseRead, summary="Update case", tags=["Cases"])
def update_case(case_id: int, patch: CaseBase, db: Session = Depends(get_db)):
    """
    Update the metadata (not relationships) for a case.
    """
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    case.title = patch.title
    case.description = patch.description
    case.crime_scene = patch.crime_scene
    db.commit()
    db.refresh(case)
    return case

# PUBLIC_INTERFACE
@app.delete("/cases/{case_id}", status_code=204, summary="Delete a case", tags=["Cases"])
def delete_case(case_id: int, db: Session = Depends(get_db)):
    """
    Delete a case and all related suspects, clues, twists, and solution.
    """
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    db.delete(case)
    db.commit()
    return JSONResponse(status_code=204, content=None)

#
# ---- CRUD for Suspects ----
#
# PUBLIC_INTERFACE
@app.post("/cases/{case_id}/suspects", response_model=SuspectRead, status_code=201, summary="Add suspect", tags=["Suspects"])
def add_suspect(case_id: int, suspect: SuspectCreate, db: Session = Depends(get_db)):
    """
    Add a suspect to a case.
    """
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    db_suspect = Suspect(
        name=suspect.name,
        description=suspect.description,
        attributes=suspect.attributes,
        case_id=case_id
    )
    db.add(db_suspect)
    db.commit()
    db.refresh(db_suspect)
    return db_suspect

# PUBLIC_INTERFACE
@app.get("/cases/{case_id}/suspects", response_model=List[SuspectRead], summary="List suspects in case", tags=["Suspects"])
def list_suspects(case_id: int, db: Session = Depends(get_db)):
    """
    List all suspects in a case.
    """
    suspects = db.query(Suspect).filter(Suspect.case_id == case_id).all()
    return suspects

# PUBLIC_INTERFACE
@app.get("/suspects/{suspect_id}", response_model=SuspectRead, summary="Get suspect", tags=["Suspects"])
def get_suspect(suspect_id: int, db: Session = Depends(get_db)):
    """
    Get details for a suspect by ID.
    """
    suspect = db.query(Suspect).filter(Suspect.id == suspect_id).first()
    if not suspect:
        raise HTTPException(status_code=404, detail="Suspect not found")
    return suspect

# PUBLIC_INTERFACE
@app.put("/suspects/{suspect_id}", response_model=SuspectRead, summary="Update suspect", tags=["Suspects"])
def update_suspect(suspect_id: int, patch: SuspectBase, db: Session = Depends(get_db)):
    """
    Update an existing suspect.
    """
    suspect = db.query(Suspect).filter(Suspect.id == suspect_id).first()
    if not suspect:
        raise HTTPException(status_code=404, detail="Suspect not found")
    suspect.name = patch.name
    suspect.description = patch.description
    suspect.attributes = patch.attributes
    db.commit()
    db.refresh(suspect)
    return suspect

# PUBLIC_INTERFACE
@app.delete("/suspects/{suspect_id}", status_code=204, summary="Delete suspect", tags=["Suspects"])
def delete_suspect(suspect_id: int, db: Session = Depends(get_db)):
    """
    Delete a suspect.
    """
    suspect = db.query(Suspect).filter(Suspect.id == suspect_id).first()
    if not suspect:
        raise HTTPException(status_code=404, detail="Suspect not found")
    db.delete(suspect)
    db.commit()
    return JSONResponse(status_code=204, content=None)

#
# ---- CRUD for Clues ----
#
# PUBLIC_INTERFACE
@app.post("/cases/{case_id}/clues", response_model=ClueRead, status_code=201, summary="Add clue", tags=["Clues"])
def add_clue(case_id: int, clue: ClueCreate, db: Session = Depends(get_db)):
    """
    Add a clue to a case.
    """
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    db_clue = Clue(
        clue_type=clue.clue_type,
        description=clue.description,
        case_id=case_id
    )
    db.add(db_clue)
    db.commit()
    db.refresh(db_clue)
    return db_clue

# PUBLIC_INTERFACE
@app.get("/cases/{case_id}/clues", response_model=List[ClueRead], summary="List clues in case", tags=["Clues"])
def list_clues(case_id: int, db: Session = Depends(get_db)):
    """
    List all clues in a case.
    """
    clues = db.query(Clue).filter(Clue.case_id == case_id).all()
    return clues

# PUBLIC_INTERFACE
@app.get("/clues/{clue_id}", response_model=ClueRead, summary="Get clue", tags=["Clues"])
def get_clue(clue_id: int, db: Session = Depends(get_db)):
    """
    Get details for a clue by ID.
    """
    clue = db.query(Clue).filter(Clue.id == clue_id).first()
    if not clue:
        raise HTTPException(status_code=404, detail="Clue not found")
    return clue

# PUBLIC_INTERFACE
@app.put("/clues/{clue_id}", response_model=ClueRead, summary="Update clue", tags=["Clues"])
def update_clue(clue_id: int, patch: ClueBase, db: Session = Depends(get_db)):
    """
    Update an existing clue.
    """
    clue = db.query(Clue).filter(Clue.id == clue_id).first()
    if not clue:
        raise HTTPException(status_code=404, detail="Clue not found")
    clue.clue_type = patch.clue_type
    clue.description = patch.description
    db.commit()
    db.refresh(clue)
    return clue

# PUBLIC_INTERFACE
@app.delete("/clues/{clue_id}", status_code=204, summary="Delete clue", tags=["Clues"])
def delete_clue(clue_id: int, db: Session = Depends(get_db)):
    """
    Delete a clue.
    """
    clue = db.query(Clue).filter(Clue.id == clue_id).first()
    if not clue:
        raise HTTPException(status_code=404, detail="Clue not found")
    db.delete(clue)
    db.commit()
    return JSONResponse(status_code=204, content=None)

#
# ---- CRUD for Twists (Contradictions) ----
#
# PUBLIC_INTERFACE
@app.post("/cases/{case_id}/twists", response_model=TwistRead, status_code=201, summary="Add twist", tags=["Twists"])
def add_twist(case_id: int, twist: TwistCreate, db: Session = Depends(get_db)):
    """
    Add a twist or contradiction to a case.
    """
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    db_twist = Twist(
        description=twist.description,
        case_id=case_id
    )
    db.add(db_twist)
    db.commit()
    db.refresh(db_twist)
    return db_twist

# PUBLIC_INTERFACE
@app.get("/cases/{case_id}/twists", response_model=List[TwistRead], summary="List twists/contradictions", tags=["Twists"])
def list_twists(case_id: int, db: Session = Depends(get_db)):
    """
    List all twists or contradictions for a case.
    """
    twists = db.query(Twist).filter(Twist.case_id == case_id).all()
    return twists

# PUBLIC_INTERFACE
@app.get("/twists/{twist_id}", response_model=TwistRead, summary="Get twist", tags=["Twists"])
def get_twist(twist_id: int, db: Session = Depends(get_db)):
    """
    Get details for a twist by ID.
    """
    twist = db.query(Twist).filter(Twist.id == twist_id).first()
    if not twist:
        raise HTTPException(status_code=404, detail="Twist not found")
    return twist

# PUBLIC_INTERFACE
@app.put("/twists/{twist_id}", response_model=TwistRead, summary="Update twist", tags=["Twists"])
def update_twist(twist_id: int, patch: TwistBase, db: Session = Depends(get_db)):
    """
    Update an existing twist.
    """
    twist = db.query(Twist).filter(Twist.id == twist_id).first()
    if not twist:
        raise HTTPException(status_code=404, detail="Twist not found")
    twist.description = patch.description
    db.commit()
    db.refresh(twist)
    return twist

# PUBLIC_INTERFACE
@app.delete("/twists/{twist_id}", status_code=204, summary="Delete twist", tags=["Twists"])
def delete_twist(twist_id: int, db: Session = Depends(get_db)):
    """
    Delete a twist.
    """
    twist = db.query(Twist).filter(Twist.id == twist_id).first()
    if not twist:
        raise HTTPException(status_code=404, detail="Twist not found")
    db.delete(twist)
    db.commit()
    return JSONResponse(status_code=204, content=None)

#
# ---- CRUD for Solutions ----
#
# PUBLIC_INTERFACE
@app.post("/cases/{case_id}/solution", response_model=SolutionRead, status_code=201, summary="Add solution", tags=["Solutions"])
def add_solution(case_id: int, solution: SolutionCreate, db: Session = Depends(get_db)):
    """
    Add solution to a case. Only one per case. Overwrites existing if present.
    """
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    db_solution = db.query(Solution).filter(Solution.case_id == case_id).first()
    if db_solution:
        db_solution.summary = solution.summary
        db_solution.how_solved = solution.how_solved
    else:
        db_solution = Solution(
            summary=solution.summary,
            how_solved=solution.how_solved,
            case_id=case_id,
        )
        db.add(db_solution)
    db.commit()
    db.refresh(db_solution)
    return db_solution

# PUBLIC_INTERFACE
@app.get("/cases/{case_id}/solution", response_model=SolutionRead, summary="Get solution for case", tags=["Solutions"])
def get_solution(case_id: int, db: Session = Depends(get_db)):
    """
    Get the solution for a case.
    """
    solution = db.query(Solution).filter(Solution.case_id == case_id).first()
    if not solution:
        raise HTTPException(status_code=404, detail="Solution not found")
    return solution

# PUBLIC_INTERFACE
@app.delete("/cases/{case_id}/solution", status_code=204, summary="Delete solution from case", tags=["Solutions"])
def delete_solution(case_id: int, db: Session = Depends(get_db)):
    """
    Delete a solution for a case.
    """
    solution = db.query(Solution).filter(Solution.case_id == case_id).first()
    if not solution:
        raise HTTPException(status_code=404, detail="Solution not found")
    db.delete(solution)
    db.commit()
    return JSONResponse(status_code=204, content=None)

#
# ---- Game Logic: Contradictions, Twists, Solution Validation ----
#
# PUBLIC_INTERFACE
@app.get("/cases/{case_id}/contradictions", response_model=List[Dict[str, Any]], summary="Analyze case for contradictions/twists", tags=["Gameplay"])
def find_contradictions(case_id: int, db: Session = Depends(get_db)):
    """
    Returns a summary list of contradictions/twists in a case.
    Contradictions are fetched from the 'twists' linked to the case.
    Could be extended to auto-detect new contradictions via simple analysis (TODO).
    """
    twists = db.query(Twist).filter(Twist.case_id == case_id).all()
    result = [{"id": t.id, "description": t.description} for t in twists]
    # Placeholder: real contradiction detection (cross-check clues/suspect statements) could go here as future work.
    return result

# PUBLIC_INTERFACE
@app.post("/cases/{case_id}/validate_solution", response_model=dict, summary="Validate provided solution for case", tags=["Gameplay"])
def validate_solution(case_id: int, submitted_solution: SolutionBase, db: Session = Depends(get_db)):
    """
    Validates user's answer against the official solution (case-insensitive substring match in summary).
    This endpoint can be used to provide immediate feedback for the player's theory or submission.
    """
    solution = db.query(Solution).filter(Solution.case_id == case_id).first()
    if not solution:
        raise HTTPException(status_code=404, detail="Solution not found")
    # Compare submitted vs. stored official solution
    match = (
        submitted_solution.summary.strip().lower() in solution.summary.strip().lower()
        or solution.summary.strip().lower() in submitted_solution.summary.strip().lower()
    )
    return {
        "valid": match,
        "official_solution": solution.summary if match else None
    }

# PUBLIC_INTERFACE
@app.get("/cases/{case_id}/twist_highlights", response_model=List[str], summary="Highlight twist/contradiction markers", tags=["Gameplay"])
def highlight_twist_terms(case_id: int, db: Session = Depends(get_db)):
    """
    Returns a list of descriptive phrases from twists to highlight as contradiction markers in the UI.
    """
    twists = db.query(Twist).filter(Twist.case_id == case_id).all()
    highlights = []
    for t in twists:
        # Heuristic: highlight the most "noteworthy" phrase in each (here simply first sentence or whole description)
        phrase = t.description.split(".")[0].strip()
        highlights.append(phrase if phrase else t.description)
    return highlights

#
# ---- Additional Utility/Meta Endpoints ----
#
# PUBLIC_INTERFACE
@app.get("/openapi.json", include_in_schema=False)
def overridden_openapi():
    """
    Serve the OpenAPI spec at the canonical location for client tools.
    """
    return app.openapi()

# PUBLIC_INTERFACE
@app.get("/usage", summary="WebSocket/gameplay API notes", tags=["Utility"])
def api_usage_doc():
    """
    Provides additional API usage/connection notes, especially useful if the API is extended with
    real-time/gameplay or websocket-based features in the future.
    """
    notes = (
        "This API provides all HTTP endpoints needed for CRUD and gameplay for Suspect Finder. "
        "If live game or collaborative play is added, consider WebSocket endpoints for real-time communication. "
        "See /docs for full OpenAPI reference."
    )
    return {"usage_notes": notes}
