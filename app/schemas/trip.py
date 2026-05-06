from pydantic import BaseModel, Field
from typing import Literal, Optional


class TripRequest(BaseModel):
    destination: str = Field(..., description="Destino da viagem (cidade, país ou região)")
    days: int = Field(..., ge=1, le=30, description="Quantidade de dias da viagem")
    travelers: int = Field(1, ge=1, description="Número de viajantes")
    budget: Optional[str] = Field(None, description="Faixa de orçamento: baixo, médio, alto")
    preferences: Optional[list[str]] = Field(
        default_factory=list,
        description="Preferências: ex. cultura, gastronomia, aventura, natureza, compras",
    )
    accommodation: Optional[str] = Field(None, description="Tipo de hospedagem preferido")
    mobility_restrictions: Optional[bool] = Field(False, description="Possui restrição de mobilidade?")
    travel_style: Optional[str] = Field(
        None, description="Estilo de viagem: relaxado, intenso, moderado"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "destination": "Lisboa, Portugal",
                "days": 5,
                "travelers": 2,
                "budget": "médio",
                "preferences": ["cultura", "gastronomia", "história"],
                "accommodation": "hotel",
                "mobility_restrictions": False,
                "travel_style": "moderado",
            }
        }
    }


class Coordinates(BaseModel):
    lat: float
    lng: float


class MapPin(BaseModel):
    day: int
    time: str
    activity: str
    location: str
    type: Literal["passeio", "restaurante", "hospedagem", "transporte"]
    coordinates: Coordinates


class ActivityItem(BaseModel):
    time: str
    activity: str
    location: str
    tips: Optional[str] = None
    estimated_cost: Optional[str] = Field(None, description="Custo estimado por pessoa (ex: R$ 50,00 ou Gratuito)")
    coordinates: Optional[Coordinates] = Field(None, description="Coordenadas geográficas do local")


class DayPlan(BaseModel):
    day: int
    title: str
    activities: list[ActivityItem]
    daily_cost_estimate: Optional[str] = Field(None, description="Custo total estimado do dia por pessoa")


class TripResponse(BaseModel):
    destination: str
    total_days: int
    summary: str
    itinerary: list[DayPlan]
    general_tips: list[str]
    map_pins: list[MapPin] = Field(
        default_factory=list,
        description="Todos os pins do mapa consolidados para renderização no front-end",
    )
    model_used: str
