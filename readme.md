# 🌞 Solar Power Plant Prospecting Tool — São Paulo, Brazil

A data pipeline that crosses **open government data from ANEEL** (Brazil's National Electric Energy Agency) with the **Google Maps Places API** to identify businesses that own large photovoltaic solar installations in São Paulo state — building a ready-to-use sales prospecting list.

---

## The Problem It Solves

Solar maintenance companies need to find businesses that own large solar installations — but there's no public directory that connects a power plant to its owner's phone number or address.

This tool bridges that gap: it pulls raw technical data from the government, filters plants by size and region, then uses Google Maps to identify each business and extract contact information for a sales team.

---

## How It Works

```
ANEEL Open Data API
        ↓
Filter: UFV (photovoltaic) + São Paulo + ≥ 300kW
        ↓
687,837 total records → 779 qualifying plants
        ↓
Google Maps Places API
(reverse geocoding by coordinates)
        ↓
Final CSV: business name, phone, address, installed power (kW)
```

---

## Key Features

- **Smart caching** — Google Maps API charges per request. The tool saves every result to a local JSON cache, so interruptions never cost money and re-runs are free.
- **Batch processing** — queries are sent in batches of 20 with a configurable delay, staying well within API rate limits.
- **Resume on interruption** — if the script stops mid-run, it picks up exactly where it left off using the cache.
- **Clean output** — generates a CSV formatted for direct use by a sales or business development team.

---

## Project Structure

```
projeto-aneel/
│
├── 1_filtrar_aneel.py      # Downloads and filters ANEEL data via their open API
├── 2_consultar_maps.py     # Queries Google Maps with intelligent caching
│
├── dados/                  # Auto-generated
│   └── filtrado_sp.csv     # 779 filtered solar plants
│
├── cache/                  # Auto-generated
│   └── cache_maps.json     # API response cache (avoids duplicate paid calls)
│
├── resultados/             # Auto-generated
│   └── lista_vendas.csv    # Final output list for the sales team
│
├── .env.example            # Configuration template
├── .env                    # Your credentials (not committed to Git)
├── requirements.txt        # Python dependencies
└── README.md
```

---

## Requirements

- Python 3.11+
- Google Maps API key with **Places API** enabled

---

## Setup

```bash
# 1. Clone the repository
git clone https://github.com/viniciussilva-dev/prospeccao-usinas-solares-sp.git
cd prospeccao-usinas-solares-sp

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up credentials
cp .env.example .env
# Edit .env and add your Google Maps API key
```

---

## Usage

### Step 1 — Filter ANEEL data

```bash
python 1_filtrar_aneel.py
```

Fetches data from ANEEL's public API and filters for photovoltaic plants (UFV) ≥ 300kW in São Paulo state.
Output saved to `dados/filtrado_sp.csv`.

### Step 2 — Query Google Maps

```bash
python 2_consultar_maps.py
```

Sends each plant's coordinates to the Google Maps Places API in batches of 20.
Progress is saved to the cache after each batch — safe to interrupt and resume.
Output saved to `resultados/lista_vendas.csv`.

---

## Caching System

The script uses a local JSON cache to avoid duplicate API calls:

| Scenario | Behavior |
|---|---|
| First run | Queries all 779 plants |
| Re-run after completion | Reads entirely from cache — zero API cost |
| Interrupted mid-run | Resumes from last cached result |

---

## Results

| Metric | Value |
|---|---|
| Total UFV plants in São Paulo | 687,837 |
| After ≥ 300kW filter | 779 |
| Average installed power | 1,191 kW |
| Maximum installed power | 5,000 kW |

---

## Estimated API Cost

| Request type | Count | Estimated cost |
|---|---|---|
| Nearby Search | 779 | ~US$ 24.93 |
| Place Details | 779 | ~US$ 13.24 |
| **Total** | **1,558** | **~US$ 38.00** |

> Google provides **US$ 200.00 in free monthly credits** — this project runs entirely within the free tier.

---

## Tech Stack

| Tool | Purpose |
|---|---|
| Python 3.11 | Core language |
| Pandas | Data filtering and manipulation |
| Requests | HTTP calls to ANEEL and Google APIs |
| Google Maps Places API | Reverse geocoding by coordinates |
| ANEEL Open Data API | Source of solar plant records |

---

## Data Source

[ANEEL — Distributed Generation Register](https://dadosabertos.aneel.gov.br/dataset/relacao-de-empreendimentos-de-geracao-distribuida)

Updated monthly. License: Brazilian government open data (public domain).

---

## Author

**Vinicius Silva** — [github.com/viniciussilva-dev](https://github.com/viniciussilva-dev)