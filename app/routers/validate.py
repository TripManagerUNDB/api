from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.google_maps import _client
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class ValidateDestinationRequest(BaseModel):
    destination: str


class ValidateDestinationResponse(BaseModel):
    valid: bool
    message: str
    formatted_address: str | None = None


@router.post("/validate-destination", response_model=ValidateDestinationResponse)
async def validate_destination(req: ValidateDestinationRequest):

    print("DEBUG: Recebido request: ", req)
    
    if not req.destination or len(req.destination.strip()) < 2:
        return ValidateDestinationResponse(valid=False, message="Destino muito curto.")

    try:
        gmaps = _client()
        results = gmaps.geocode(req.destination, language="pt-BR")

        if not results:
            return ValidateDestinationResponse(
                valid=False,
                message=f"Destino '{req.destination}' não encontrado. Verifique o nome da cidade ou país."
            )

        formatted = results[0].get("formatted_address", req.destination)
        return ValidateDestinationResponse(
            valid=True,
            message="Destino válido.",
            formatted_address=formatted
        )

    except Exception as exc:
        logger.warning("Erro ao validar destino '%s': %s", req.destination, exc)
        raise HTTPException(status_code=500, detail="Erro ao validar destino.")
