# TripManager — Documentação de Integração Front-end

## Visão geral

O TripManager é uma API REST construída em Python (FastAPI) que recebe dados de uma viagem, consulta restaurantes reais via Google Maps e usa um modelo de linguagem (Groq/LLaMA) para gerar um roteiro completo. A resposta já inclui as coordenadas geográficas de cada local, prontas para serem plotadas em um mapa.

O fluxo é:

```
Usuário preenche formulário
        |
        v
Front-end envia POST /trip/plan
        |
        v
API consulta Google Maps (restaurantes mais bem avaliados)
        |
        v
API envia dados + restaurantes para o modelo de IA
        |
        v
IA gera roteiro em JSON
        |
        v
API geocodifica cada local (lat/lng via Google Maps)
        |
        v
Front-end recebe roteiro com coordenadas prontas
        |
        v
Leaflet plota os pins no mapa
```

---

## Rodando a API localmente

**Requisitos:** Python 3.11+

```bash
# 1. Criar ambiente virtual
python -m venv .venv

# 2. Ativar
# Windows:
.venv\Scripts\activate
# Mac/Linux:
source .venv/bin/activate

# 3. Instalar dependências
pip install -r requirements.txt

# 4. Subir o servidor
uvicorn app.main:app --reload
```

A API estará disponível em `http://localhost:8000`.

Documentação interativa (Swagger): `http://localhost:8000/docs`

---

## Endpoint principal

### POST /trip/plan

Gera o roteiro completo com coordenadas para o mapa.

**URL:** `http://localhost:8000/trip/plan`

**Headers:**
```
Content-Type: application/json
```

---

### Corpo da requisição

```json
{
  "destination": "São Luís, Maranhão, Brasil",
  "days": 3,
  "travelers": 2,
  "budget": "médio",
  "preferences": ["gastronomia", "cultura"],
  "accommodation": "hotel",
  "mobility_restrictions": false,
  "travel_style": "moderado"
}
```

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `destination` | string | Sim | Cidade, estado ou país |
| `days` | integer | Sim | Duração da viagem (1 a 30) |
| `travelers` | integer | Não | Número de viajantes (padrão: 1) |
| `budget` | string | Não | `"baixo"`, `"médio"` ou `"alto"` |
| `preferences` | array de strings | Não | Ex: `["gastronomia", "cultura", "aventura"]` |
| `accommodation` | string | Não | Ex: `"hotel"`, `"hostel"`, `"airbnb"` |
| `mobility_restrictions` | boolean | Não | Se há restrição de mobilidade (padrão: false) |
| `travel_style` | string | Não | `"relaxado"`, `"moderado"` ou `"intenso"` |

---

### Resposta de sucesso (200 OK)

```json
{
  "destination": "São Luís, Maranhão, Brasil",
  "total_days": 3,
  "summary": "Roteiro de 3 dias explorando o centro histórico, a gastronomia típica e as belezas naturais de São Luís.",
  "itinerary": [
    {
      "day": 1,
      "title": "Centro Histórico e Gastronomia",
      "daily_cost_estimate": "R$ 120,00",
      "activities": [
        {
          "time": "09:00",
          "activity": "Visita ao Centro Histórico de São Luís",
          "location": "Rua Portugal, Centro, São Luís",
          "tips": "Chegue cedo para evitar o calor e aproveitar as ruas vazias.",
          "estimated_cost": "Gratuito",
          "coordinates": {
            "lat": -2.5297,
            "lng": -44.3028
          }
        },
        {
          "time": "13:00",
          "activity": "Almoço no Restaurante Base",
          "location": "Rua do Giz, Centro, São Luís",
          "tips": "Peça o arroz de cuxá, prato típico maranhense.",
          "estimated_cost": "R$ 45,00",
          "coordinates": {
            "lat": -2.5311,
            "lng": -44.3041
          }
        }
      ]
    }
  ],
  "general_tips": [
    "Leve protetor solar, o calor em São Luís é intenso.",
    "O período de menor chuva é de julho a dezembro."
  ],
  "map_pins": [
    {
      "day": 1,
      "time": "09:00",
      "activity": "Visita ao Centro Histórico de São Luís",
      "location": "Rua Portugal, Centro, São Luís",
      "type": "passeio",
      "coordinates": {
        "lat": -2.5297,
        "lng": -44.3028
      }
    },
    {
      "day": 1,
      "time": "13:00",
      "activity": "Almoço no Restaurante Base",
      "location": "Rua do Giz, Centro, São Luís",
      "type": "restaurante",
      "coordinates": {
        "lat": -2.5311,
        "lng": -44.3041
      }
    }
  ],
  "model_used": "llama-3.3-70b-versatile"
}
```

**Campos importantes da resposta:**

| Campo | Descrição |
|---|---|
| `itinerary` | Lista de dias com atividades detalhadas. Cada atividade tem `coordinates` para uso no mapa. |
| `map_pins` | Lista plana com todos os pins do roteiro completo. Use este campo para renderizar o mapa. |
| `map_pins[].type` | Tipo do local: `"passeio"`, `"restaurante"`, `"hospedagem"` ou `"transporte"`. Use para diferenciar ícones. |
| `map_pins[].coordinates.lat` | Latitude do local. |
| `map_pins[].coordinates.lng` | Longitude do local. |

---

### Respostas de erro

| Status | Situação |
|---|---|
| `422` | Campos obrigatórios ausentes ou inválidos |
| `502` | A IA retornou resposta em formato inválido |
| `503` | Todos os modelos de IA atingiram limite de uso (tente novamente em alguns minutos) |
| `500` | Erro interno inesperado |

---

## Como integrar o mapa com Leaflet + OpenStreetMap

A seção a seguir mostra como implementar a lat long trazida na resposta da API em um mapa visual usando a o Leaflet.

O Leaflet é uma biblioteca JavaScript gratuita e de código aberto para mapas interativos. Não requer chave de API.


### 1. Adicionar o Leaflet ao projeto

**Via CDN (HTML puro):**
```html
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
```

**Via npm (React, Vue, etc.):**
```bash
npm install leaflet
```
```js
import L from "leaflet";
import "leaflet/dist/leaflet.css";
```

---

### 2. Criar o elemento do mapa no HTML

```html
<div id="map" style="width: 100%; height: 500px;"></div>
```

O Leaflet precisa que o elemento tenha altura definida, caso contrário o mapa não aparece.

---

### 3. Inicializar o mapa

```js
const map = L.map("map").setView([0, 0], 2);

L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  attribution: '© <a href="https://openstreetmap.org">OpenStreetMap</a>',
  maxZoom: 19,
}).addTo(map);
```

---

### 4. Chamar a API e renderizar os pins

```js
async function planTrip(formData) {
  const response = await fetch("http://localhost:8000/trip/plan", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(formData),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail ?? `Erro ${response.status}`);
  }

  const data = await response.json();
  renderMapPins(data.map_pins);
  return data;
}

function renderMapPins(mapPins) {
  // Remove markers anteriores se existirem
  if (window._markers) {
    window._markers.forEach(m => map.removeLayer(m));
  }
  window._markers = [];

  mapPins.forEach(pin => {
    const marker = L.marker([pin.coordinates.lat, pin.coordinates.lng])
      .addTo(map)
      .bindPopup(`
        <strong>${pin.activity}</strong><br/>
        ${pin.location}<br/>
        <small>Dia ${pin.day} — ${pin.time}</small>
      `);

    window._markers.push(marker);
  });

  // Ajusta o zoom para mostrar todos os pins
  if (window._markers.length > 0) {
    const group = L.featureGroup(window._markers);
    map.fitBounds(group.getBounds().pad(0.2));
  }
}
```

---

### 5. Diferenciar ícones por tipo de local (opcional)

O campo `type` de cada pin pode ser `"passeio"`, `"restaurante"`, `"hospedagem"` ou `"transporte"`. Use para exibir ícones diferentes:

```js
const TYPE_EMOJI = {
  passeio:     "🏛️",
  restaurante: "🍽️",
  hospedagem:  "🏨",
  transporte:  "🚌",
};

const TYPE_COLOR = {
  passeio:     "#1a73e8",
  restaurante: "#e53935",
  hospedagem:  "#2e7d32",
  transporte:  "#f57c00",
};

function createIcon(type) {
  const emoji = TYPE_EMOJI[type] ?? "📍";
  const color = TYPE_COLOR[type] ?? "#555";

  return L.divIcon({
    className: "",
    html: `
      <div style="
        background: ${color};
        color: #fff;
        border-radius: 50% 50% 50% 0;
        transform: rotate(-45deg);
        width: 36px;
        height: 36px;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 2px 6px rgba(0,0,0,0.35);
        font-size: 16px;
      ">
        <span style="transform: rotate(45deg)">${emoji}</span>
      </div>
    `,
    iconSize: [36, 36],
    iconAnchor: [18, 36],
    popupAnchor: [0, -36],
  });
}

// Uso ao criar o marker:
const marker = L.marker(
  [pin.coordinates.lat, pin.coordinates.lng],
  { icon: createIcon(pin.type) }
).addTo(map);
```

---

### 6. Filtrar pins por dia (opcional)

Se a interface tiver abas por dia, use o campo `day` para filtrar:

```js
function showDay(dayNumber) {
  // Remove todos os markers
  window._markers.forEach(({ marker }) => map.removeLayer(marker));

  // Adiciona apenas os do dia selecionado
  window._markers
    .filter(({ pin }) => pin.day === dayNumber)
    .forEach(({ marker }) => marker.addTo(map));
}
```

Para isso, guarde referência ao pin junto com o marker:
```js
window._markers = mapPins.map(pin => {
  const marker = L.marker([pin.coordinates.lat, pin.coordinates.lng], {
    icon: createIcon(pin.type),
  }).bindPopup(`<strong>${pin.activity}</strong><br/>${pin.location}`);

  return { pin, marker };
});
```

---

## Estrutura de dados resumida

```
POST /trip/plan
  |
  |-- itinerary[]
  |     |-- day: número do dia
  |     |-- title: tema do dia
  |     |-- daily_cost_estimate: custo total do dia por pessoa
  |     |-- activities[]
  |           |-- time: horário
  |           |-- activity: nome da atividade
  |           |-- location: endereço
  |           |-- tips: dica prática
  |           |-- estimated_cost: custo por pessoa
  |           |-- coordinates: { lat, lng }   <-- para popup de detalhe
  |
  |-- map_pins[]   <-- use este para renderizar o mapa
        |-- day
        |-- time
        |-- activity
        |-- location
        |-- type: passeio | restaurante | hospedagem | transporte
        |-- coordinates: { lat, lng }
```

---

## CORS

A API já está configurada para aceitar requisições de qualquer origem (`*`). Nenhuma configuração adicional é necessária no front-end para desenvolvimento local.

---

## Referência rápida

| Recurso | URL |
|---|---|
| API local | `http://localhost:8000` |
| Swagger (documentação interativa) | `http://localhost:8000/docs` |
| Health check | `http://localhost:8000/health` |
| Leaflet docs | https://leafletjs.com/reference.html |
| OpenStreetMap tiles | `https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png` |
