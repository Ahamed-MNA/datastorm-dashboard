from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db.session import get_db
from app.models.schemas import OutletXAIResponseSchema
from app.services.xai_service import XaiService

router = APIRouter(prefix="/api/xai", tags=["xai"])

@router.get("/{outlet_id}/explanation", response_model=OutletXAIResponseSchema)
def get_outlet_explanation_text(outlet_id: str):
    """
    Get the 3-paragraph business explanation narrative along with metadata for an outlet.
    """
    try:
        explanation = XaiService.get_outlet_explanation(outlet_id)
        return explanation
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate explanation: {e}")

@router.get("/{outlet_id}", response_model=OutletXAIResponseSchema)
def get_outlet_explanation(outlet_id: str):
    return get_outlet_explanation_text(outlet_id)
