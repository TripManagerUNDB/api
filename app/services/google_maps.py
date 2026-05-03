import logging
import googlemaps
from app.core.config import settings

logger = logging.getLogger(__name__)

PRICE_LEVEL_MAP = {
    0: "Gratuito",
    1: "Barato (até R$ 30)",
    2: "Moderado (R$ 30–80)",
    3: "Caro (R$ 80–150)",
    4: "Muito caro (acima de R$ 150)",
}


def _client() -> googlemaps.Client:
    return googlemaps.Client(key=settings.GOOGLE_MAPS_API_KEY)


def fetch_top_restaurants(destination: str, max_results: int = 10) -> list[dict]:
    """
    Busca os restaurantes mais bem avaliados para um destino via Google Places API.
    Retorna lista com nome, nota, número de avaliações, tipos de culinária e faixa de preço.
    """
    try:
        gmaps = _client()

        results = gmaps.places(
            query=f"melhores restaurantes em {destination}",
            language="pt-BR",
            type="restaurant",
        )

        places = results.get("results", [])

        # Ordena por rating e número de avaliações para priorizar os mais relevantes
        places.sort(
            key=lambda p: (p.get("rating", 0), p.get("user_ratings_total", 0)),
            reverse=True,
        )

        restaurants = []
        for place in places[:max_results]:
            name = place.get("name", "")
            rating = place.get("rating")
            total_ratings = place.get("user_ratings_total", 0)
            price_level = place.get("price_level")
            types = place.get("types", [])

            # Filtra tipos genéricos do Google e formata culinária
            cuisine_types = [
                t.replace("_", " ").title()
                for t in types
                if t not in (
                    "restaurant", "food", "point_of_interest",
                    "establishment", "meal_delivery", "meal_takeaway",
                )
            ]

            restaurants.append({
                "name": name,
                "rating": rating,
                "total_ratings": total_ratings,
                "price_level": PRICE_LEVEL_MAP.get(price_level, "Não informado") if price_level is not None else "Não informado",
                "cuisine": ", ".join(cuisine_types[:3]) if cuisine_types else "Não especificado",
            })

        logger.info("Google Maps retornou %d restaurantes para '%s'", len(restaurants), destination)
        return restaurants

    except Exception as exc:
        logger.warning("Falha ao buscar restaurantes no Google Maps: %s", exc)
        return []


def format_restaurants_for_prompt(restaurants: list[dict]) -> str:
    """Formata a lista de restaurantes para ser injetada no prompt."""
    if not restaurants:
        return ""

    lines = ["Restaurantes mais bem avaliados no Google Maps para este destino:\n"]
    for i, r in enumerate(restaurants, 1):
        rating_str = f"{r['rating']} ⭐ ({r['total_ratings']} avaliações)" if r["rating"] else "sem avaliação"
        lines.append(
            f"{i}. {r['name']} — {rating_str} | Culinária: {r['cuisine']} | Preço: {r['price_level']}"
        )

    return "\n".join(lines)


# Palavras-chave que indicam o tipo de atividade para o pin do mapa
_RESTAURANT_KEYWORDS = {"restaurante", "almoço", "jantar", "café", "lanche", "bistrô", "bar", "brunch", "refeição"}
_TRANSPORT_KEYWORDS = {"táxi", "uber", "metrô", "ônibus", "trem", "ferry", "barco", "transfer", "aeroporto"}
_ACCOMMODATION_KEYWORDS = {"hotel", "hostel", "pousada", "airbnb", "hospedagem", "check-in", "check-out"}


def _infer_pin_type(activity: str) -> str:
    activity_lower = activity.lower()
    if any(k in activity_lower for k in _RESTAURANT_KEYWORDS):
        return "restaurante"
    if any(k in activity_lower for k in _TRANSPORT_KEYWORDS):
        return "transporte"
    if any(k in activity_lower for k in _ACCOMMODATION_KEYWORDS):
        return "hospedagem"
    return "passeio"


def geocode_locations(locations: list[str], destination: str) -> dict[str, dict | None]:
    """
    Geocodifica uma lista de nomes de locais usando o contexto do destino.
    Retorna um dict { location_name: {"lat": ..., "lng": ...} | None }.
    Locais não encontrados recebem None.
    """
    gmaps = _client()
    results: dict[str, dict | None] = {}

    # Deduplica mantendo ordem para evitar chamadas desnecessárias
    seen: set[str] = set()
    unique_locations = [loc for loc in locations if loc not in seen and not seen.add(loc)]  # type: ignore[func-returns-value]

    for location in unique_locations:
        if not location:
            results[location] = None
            continue
        try:
            query = f"{location}, {destination}"
            geocode_result = gmaps.geocode(query, language="pt-BR")
            if geocode_result:
                geo = geocode_result[0]["geometry"]["location"]
                results[location] = {"lat": geo["lat"], "lng": geo["lng"]}
                logger.debug("Geocodificado '%s' → %s", location, results[location])
            else:
                logger.warning("Nenhum resultado de geocode para '%s'", query)
                results[location] = None
        except Exception as exc:
            logger.warning("Erro ao geocodificar '%s': %s", location, exc)
            results[location] = None

    return results
