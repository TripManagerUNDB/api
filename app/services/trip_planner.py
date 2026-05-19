import json
import logging
import re
from app.schemas.trip import TripRequest, TripResponse, DayPlan, ActivityItem, Coordinates, MapPin
from app.services.groq_client import chat_with_retry
from app.services.google_maps import (
    fetch_top_restaurants,
    format_restaurants_for_prompt,
    geocode_locations,
    _infer_pin_type,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Você é um especialista em turismo e planejamento de viagens.
Sua tarefa é criar roteiros de viagem detalhados, práticos e personalizados.
IMPORTANTE: Sempre responda em português do Brasil (pt-BR), independente do destino da viagem.
Sempre responda APENAS com JSON válido, sem texto adicional antes ou depois do JSON.
"""


def _build_user_prompt(req: TripRequest, restaurants_info: str) -> str:
    preferences_str = ", ".join(req.preferences) if req.preferences else "geral"

    restaurant_section = ""
    if restaurants_info:
        restaurant_section = f"""
{restaurants_info}

Ao montar o roteiro gastronômico, PRIORIZE os restaurantes da lista acima.
Distribua-os ao longo dos dias de forma equilibrada, sem repetir o mesmo restaurante.
Se a lista não tiver restaurantes suficientes para todos os dias, complete com sugestões relevantes para o destino.
"""

    return f"""Crie um roteiro completo de viagem com os seguintes dados:

- Destino: {req.destination}
- Duração: {req.days} dias
- Viajantes: {req.travelers} pessoa(s)
- Orçamento: {req.budget or "não informado"}
- Preferências: {preferences_str}
- Hospedagem: {req.accommodation or "não informada"}
- Restrição de mobilidade: {"sim" if req.mobility_restrictions else "não"}
- Estilo de viagem: {req.travel_style or "moderado"}
{restaurant_section}
Responda SEMPRE em português do Brasil (pt-BR).

Retorne SOMENTE o seguinte JSON (sem markdown, sem blocos de código):
{{
  "destination": "<destino>",
  "total_days": <número de dias>,
  "summary": "<resumo geral da viagem em 2-3 frases>",
  "itinerary": [
    {{
      "day": 1,
      "title": "<tema do dia>",
      "activities": [
        {{
          "time": "09:00",
          "activity": "<nome da atividade>",
          "location": "<nome do local ou endereço>",
          "tips": "<dica prática opcional>",
          "estimated_cost": "<custo estimado por pessoa, ex: R$ 50,00 ou Gratuito>"
        }}
      ],
      "daily_cost_estimate": "<soma estimada de todos os custos do dia por pessoa, ex: R$ 180,00>"
    }}
  ],
  "general_tips": [
    "<dica geral 1>",
    "<dica geral 2>"
  ]
}}

Regras importantes:
- Inclua de 4 a 6 atividades por dia com horários realistas.
- Para refeições: use os restaurantes da lista fornecida (quando disponível), incluindo nome, nota e tipo de culinária.
- Para passeios e atrações: inclua o valor do ingresso (ou "Gratuito" se for de entrada livre).
- Para transporte entre pontos: inclua o custo estimado (táxi, metrô, ônibus etc.).
- O campo "daily_cost_estimate" deve somar todos os custos do dia por pessoa.
- Use a moeda local do destino nos valores.
- Todos os textos devem estar em português do Brasil.
"""


def _extract_json(raw: str) -> dict:
    raw = raw.strip()
    # Remove possíveis blocos markdown como ```json ... ```
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    # Tenta capturar apenas o bloco JSON principal
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        raw = match.group(0)
    return json.loads(raw)


def generate_trip_plan(req: TripRequest) -> TripResponse:
    restaurants = fetch_top_restaurants(req.destination, max_results=10)
    restaurants_info = format_restaurants_for_prompt(restaurants)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": _build_user_prompt(req, restaurants_info)},
    ]

    raw_content, model_used = chat_with_retry(messages, temperature=0.7, max_tokens=8192)

    try:
        data = _extract_json(raw_content)
    except (json.JSONDecodeError, ValueError) as exc:
        logger.error("Falha ao parsear JSON da resposta: %s\nResposta bruta: %s", exc, raw_content)
        raise ValueError(f"A IA retornou uma resposta em formato inválido: {exc}") from exc

    # Coleta todos os locais únicos para geocodificar em lote
    all_locations = [
        act["location"]
        for day in data.get("itinerary", [])
        for act in day.get("activities", [])
        if act.get("location")
    ]
    
    # Geocodifica o centro da cidade como fallback
    city_center = geocode_locations([req.destination], req.destination)
    fallback_coords = city_center.get(req.destination)

    coords_map = geocode_locations(all_locations, req.destination)

    itinerary: list[DayPlan] = []
    map_pins: list[MapPin] = []

    for day in data.get("itinerary", []):
        activities: list[ActivityItem] = []
        for act in day.get("activities", []):
            location = act.get("location", "")
            geo = coords_map.get(location) or fallback_coords
            coordinates = Coordinates(**geo) if geo else None

            activities.append(ActivityItem(
                time=act["time"],
                activity=act["activity"],
                location=location,
                tips=act.get("tips"),
                estimated_cost=act.get("estimated_cost"),
                coordinates=coordinates,
            ))

            if coordinates:
                map_pins.append(MapPin(
                    day=day["day"],
                    time=act["time"],
                    activity=act["activity"],
                    location=location,
                    type=_infer_pin_type(act["activity"]),
                    coordinates=coordinates,
                ))

        itinerary.append(DayPlan(
            day=day["day"],
            title=day["title"],
            activities=activities,
            daily_cost_estimate=day.get("daily_cost_estimate"),
        ))

    return TripResponse(
        destination=data.get("destination", req.destination),
        total_days=data.get("total_days", req.days),
        summary=data.get("summary", ""),
        itinerary=itinerary,
        general_tips=data.get("general_tips", []),
        map_pins=map_pins,
        model_used=model_used,
    )
