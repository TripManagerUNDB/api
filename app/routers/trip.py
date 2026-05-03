from fastapi import APIRouter, HTTPException, status
from app.schemas.trip import TripRequest, TripResponse
from app.services.trip_planner import generate_trip_plan
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/trip", tags=["Trip Planner"])


@router.post(
    "/plan",
    response_model=TripResponse,
    status_code=status.HTTP_200_OK,
    summary="Gerar roteiro de viagem",
    description="Recebe informações da viagem e retorna um roteiro detalhado com atividades, restaurantes e dicas.",
)
async def plan_trip(req: TripRequest) -> TripResponse:
    try:
        return generate_trip_plan(req)
    except RuntimeError as exc:
        logger.error("Todos os modelos falharam: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Serviço temporariamente indisponível. Todos os modelos atingiram o limite de uso.",
        )
    except ValueError as exc:
        logger.error("Erro de validação na resposta da IA: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        )
    except Exception as exc:
        logger.exception("Erro inesperado ao gerar roteiro: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao processar sua solicitação.",
        )
