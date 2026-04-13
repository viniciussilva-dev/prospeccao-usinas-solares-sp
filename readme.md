# 🌞 Prospecção de Usinas Solares — SP

Ferramenta de prospecção de clientes que cruza dados abertos da **ANEEL** com a **Google Maps API** e **Google Solar API** para identificar empresas donas de usinas fotovoltaicas grandes em São Paulo — e descobrir o potencial de expansão de cada uma.

## Objetivo

Encontrar estabelecimentos comerciais com usinas solares instaladas acima de 300kW para oferecer serviços de manutenção e expansão. O resultado é uma lista com nome, telefone, endereço e potencial de crescimento de cada estabelecimento.

## Como funciona

```
ANEEL (dados abertos)
        ↓
Filtra: UFV + SP + ≥300kW
        ↓
687.837 registros → 779 usinas
        ↓
Google Maps Places API          Google Solar API
(nome, telefone, endereço)      (telhado, painéis, expansão)
        ↓                               ↓
        └──────────┬────────────────────┘
                   ↓
        Lista final para vendedores
        (com potencial de expansão ordenado)
```

## Estrutura do projeto

```
projeto-aneel/
│
├── 1_filtrar_aneel.py      # Baixa e filtra dados da ANEEL via API
├── 2_consultar_maps.py     # Consulta Google Maps com cache SQLite
├── 3_solar_api.py          # Consulta Solar API — potencial de expansão
│
├── dados/                  # Gerado automaticamente
│   └── filtrado_sp.csv     # 779 usinas filtradas
│
├── cache/                  # Gerado automaticamente
│   └── cache.db            # Banco SQLite com cache de todas as consultas
│
├── resultados/             # Gerado automaticamente
│   ├── lista_vendas.csv         # Lista com nome, tel, endereço
│   └── lista_vendas_solar.csv   # Lista completa com dados solares
│
├── .env.example            # Modelo de configuração
├── .env                    # Suas credenciais (não sobe no GitHub)
├── requirements.txt        # Dependências
└── README.md
```

## Pré-requisitos

- Python 3.11+
- Chave da API do Google Maps com as seguintes APIs ativadas:
  - **Places API**
  - **Solar API**

## Instalação

```bash
# 1. Clone o repositório
git clone https://github.com/viniciussilva-dev/prospeccao-usinas-solares-sp.git
cd prospeccao-usinas-solares-sp

# 2. Instale as dependências
pip install -r requirements.txt

# 3. Configure as credenciais
cp .env.example .env
# Edite o .env e coloque sua chave do Google Maps
```

## Como usar

### Passo 1 — Filtrar dados da ANEEL
```bash
python 1_filtrar_aneel.py
```
Baixa os dados via API da ANEEL e filtra as usinas UFV ≥300kW em SP.
Resultado salvo em `dados/filtrado_sp.csv`.

### Passo 2 — Consultar Google Maps
```bash
python 2_consultar_maps.py
```
Consulta o Google Maps para cada usina em lotes de 20.
Salva progresso no banco SQLite a cada lote.
Resultado salvo em `resultados/lista_vendas.csv`.

### Passo 3 — Consultar Solar API
```bash
python 3_solar_api.py
```
Para cada usina, analisa o telhado via satélite e retorna o potencial de expansão solar.
A lista final é ordenada pelo **maior potencial de expansão** — os melhores leads primeiro.
Resultado salvo em `resultados/lista_vendas_solar.csv`.

## Sistema de cache — SQLite

Todos os scripts usam um banco SQLite (`cache/cache.db`) com duas tabelas:

```sql
cache_maps   -- resultados do Google Maps Places
cache_solar  -- resultados da Google Solar API
```

Isso garante que:
- Se o script for interrompido, continua de onde parou
- Nas próximas execuções, não repete consultas já feitas
- Zero custo adicional para dados já consultados

## O que a Solar API retorna

| Campo | Descrição | Exemplo |
|---|---|---|
| Área Telhado m² | Área total disponível no telhado | 16.482 m² |
| Máx Painéis | Quantos painéis cabem | 412 painéis |
| Horas Sol/Ano | Horas de sol por ano no local | 1.498 h |
| Potência Máx kW | Potência máxima possível | 3.025 kW |
| **Potencial Expansão kW** | **Quanto ainda pode instalar** | **+2.025 kW** |
| Economia Anual USD | Economia estimada por ano | US$ 12.400 |
| Offset Carbono | Redução de CO2 kg/MWh | 87,3 kg/MWh |

## Resultados dos testes

| Dado | Valor |
|---|---|
| Usinas UFV em SP | 687.837 |
| Após filtro ≥300kW | 779 |
| Potência média | 1.191 kW |
| Com dados solares retornados | 361 (46%) |

### Top 3 maiores potenciais de expansão

| Município | Empresa | Instalado | Expansão | Telhado |
|---|---|---|---|---|
| Lençóis Paulista | Cooperativa Terenas | 1.000 kW | **+2.025 kW** | 16.482 m² |
| Carapicuíba | FAT Empreendimentos | 375 kW | **+1.531 kW** | 11.058 m² |
| Sorocaba | DPR Telecomunicações | 300 kW | **+1.176 kW** | 9.023 m² |

## Custo estimado das APIs

| API | Qtd consultas | Custo estimado |
|---|---|---|
| Maps Nearby Search | 779 | ~US$ 24,93 |
| Maps Place Details | 779 | ~US$ 13,24 |
| Solar API | 779 | ~US$ 7,80 |
| **Total** | **2.337** | **~US$ 46,00** |

O Google oferece **US$ 200,00 de crédito grátis por mês** — o projeto roda inteiro dentro do gratuito.

## Tecnologias

- **Python 3.11**
- **Pandas** — manipulação de dados
- **Requests** — chamadas HTTP
- **SQLite** — cache local das consultas
- **Google Maps Places API** — nome, telefone e endereço
- **Google Solar API** — potencial solar do telhado via satélite
- **ANEEL Dados Abertos** — fonte dos dados de usinas

## Fonte dos dados

[ANEEL — Relação de Empreendimentos de Geração Distribuída](https://dadosabertos.aneel.gov.br/dataset/relacao-de-empreendimentos-de-geracao-distribuida)

Atualização mensal. Licença: dados públicos do governo brasileiro.