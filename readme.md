# 🌞 Prospecção de Usinas Solares — SP

Ferramenta de prospecção de clientes que cruza dados abertos da **ANEEL** com a **API do Google Maps** para identificar empresas donas de usinas fotovoltaicas grandes em São Paulo.

## Objetivo

Encontrar estabelecimentos comerciais com usinas solares instaladas acima de 300kW para oferecer serviços de manutenção. O resultado é uma lista com nome, telefone e endereço de cada estabelecimento.

## Como funciona

```
ANEEL (dados abertos)
        ↓
Filtra: UFV + SP + ≥300kW
        ↓
687.837 registros → 779 usinas
        ↓
Google Maps Places API
(busca por coordenadas)
        ↓
Lista final para vendedores
```

## Estrutura do projeto

```
projeto-aneel/
│
├── 1_filtrar_aneel.py      # Baixa e filtra dados da ANEEL via API
├── 2_consultar_maps.py     # Consulta Google Maps com cache inteligente
│
├── dados/                  # Gerado automaticamente
│   └── filtrado_sp.csv     # 779 usinas filtradas
│
├── cache/                  # Gerado automaticamente
│   └── cache_maps.json     # Cache das consultas (não repete chamadas pagas)
│
├── resultados/             # Gerado automaticamente
│   └── lista_vendas.csv    # Lista final para vendedores
│
├── .env.example            # Modelo de configuração
├── .env                    # Suas credenciais (não sobe no GitHub)
├── requirements.txt        # Dependências
└── README.md
```

## Pré-requisitos

- Python 3.11+
- Chave da API do Google Maps com **Places API** ativada

## Instalação

```bash
# 1. Clone o repositório
git clone https://github.com/seu-usuario/projeto-aneel.git
cd projeto-aneel

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
Salva progresso no cache a cada lote — se interrompido, continua de onde parou.
Resultado salvo em `resultados/lista_vendas.csv`.

## Sistema de cache

O script 2 usa um cache em JSON para evitar consultas duplicadas na API do Google Maps, que é paga por uso:

- Na primeira execução: consulta todas as usinas
- Nas execuções seguintes: usa o cache, sem custo adicional
- Se interrompido no meio: continua de onde parou

## Resultados

| Dado | Valor |
|---|---|
| Usinas UFV em SP | 687.837 |
| Após filtro ≥300kW | 779 |
| Potência média | 1.191 kW |
| Potência máxima | 5.000 kW |

## Custo estimado da API

| Chamada | Qtd | Custo |
|---|---|---|
| Nearby Search | 779 | ~US$ 24,93 |
| Place Details | 779 | ~US$ 13,24 |
| **Total** | **1.558** | **~US$ 38,00** |

O Google oferece **US$ 200,00 de crédito grátis por mês** — o projeto roda dentro do gratuito.

## Tecnologias

- **Python 3.11**
- **Pandas** — manipulação de dados
- **Requests** — chamadas HTTP
- **Google Maps Places API** — geocodificação reversa
- **ANEEL Dados Abertos** — fonte dos dados de usinas

## Fonte dos dados

[ANEEL — Relação de Empreendimentos de Geração Distribuída](https://dadosabertos.aneel.gov.br/dataset/relacao-de-empreendimentos-de-geracao-distribuida)

Atualização mensal. Licença: dados públicos do governo brasileiro.