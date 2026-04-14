# 🌞 Prospecção de Usinas Solares — SP

> Ferramenta de inteligência comercial para identificar empresas com usinas fotovoltaicas de grande porte em São Paulo e descobrir o potencial de expansão de cada uma.

---

## 🎯 O problema que resolve

Empresas de energia solar que oferecem serviços de **manutenção e expansão** de usinas fotovoltaicas precisam encontrar clientes que já possuem sistemas instalados — e que têm telhado disponível para crescer.

O problema: esses dados existem, mas estão dispersos. A ANEEL publica mensalmente uma base com 687 mil registros de geração distribuída no Brasil. Encontrar as empresas certas, com as coordenadas geográficas, telefone de contato e potencial de expansão calculado — manualmente — levaria semanas.

**Esta ferramenta automatiza todo esse processo em minutos.**

---

## ✅ O que faz

- Baixa e filtra automaticamente os dados públicos da ANEEL
- Cruza coordenadas geográficas com a **Google Maps Places API** para descobrir nome, telefone, endereço e site do estabelecimento
- Consulta a **Google Solar API** via satélite para calcular área do telhado, máximo de painéis e **potencial de expansão em kW**
- Exibe tudo em um **painel visual interativo** com mapa, filtros e gestão de status por vendedor
- Permite que a equipe de vendas marque o status de cada prospecto (contatado, proposta enviada, descartado) e salve observações — tudo sincronizado com banco de dados

---

## 🖥️ Interface

O sistema tem duas partes:

**Frontend** — painel visual acessado pelo navegador:
- Mapa interativo com todos os pins coloridos por status
- Cards de resumo (total de usinas, potência média, potencial de expansão)
- Painel lateral com todos os dados do estabelecimento ao clicar no pin
- Tabela filtrável por município, empresa, potência mínima e status
- Botões de status para o vendedor registrar o andamento da prospecção

**Backend** — API REST em Flask que persiste os status no MySQL:
- Vendedores diferentes veem o mesmo estado atualizado em tempo real
- Histórico de quem atualizou cada usina e quando

---

## 📊 Resultados dos testes

| Dado | Valor |
|---|---|
| Registros na base ANEEL (SP) | 687.837 |
| Após filtro UFV ≥ 300kW | 779 usinas |
| Potência média instalada | 1.192 kW |
| Com dados solares retornados | 361 (46%) |
| Maior potencial de expansão | +2.026 kW |

### Top 3 oportunidades identificadas

| Município | Empresa | Instalado | Potencial de Expansão | Telhado |
|---|---|---|---|---|
| Lençóis Paulista | Cooperativa Terenas | 1.000 kW | **+2.026 kW** | 16.482 m² |
| Carapicuíba | FAT Empreendimentos | 375 kW | **+1.532 kW** | 11.058 m² |
| Sorocaba | DPR Telecomunicações | 300 kW | **+1.176 kW** | 9.023 m² |

---

## 🗂️ Estrutura do projeto

```
projeto-aneel/
│
├── python/
│   ├── 1_filtrar_aneel.py       # Baixa e filtra dados da ANEEL via API
│   ├── 2_consultar_maps.py      # Consulta Google Maps Places API com cache
│   └── 3_solar_api.py           # Consulta Google Solar API com cache
│
├── frontend/
│   ├── index.html               # Interface principal
│   ├── css/style.css            # Visual completo
│   ├── js/dados.js              # Carrega CSVs e comunica com backend
│   ├── js/mapa.js               # Mapa Google Maps e pins interativos
│   └── js/tabela.js             # Tabela filtrável e ordenável
│
├── backend/
│   ├── app.py                   # Servidor Flask (porta 5001)
│   ├── banco.py                 # Conexão MySQL e criação de tabelas
│   └── rotas.py                 # 4 endpoints REST de status
│
├── .env.example                 # Modelo de variáveis de ambiente
├── requirements.txt             # Dependências Python
└── README.md
```

---

## ⚙️ Pré-requisitos

- Python 3.11+
- MySQL 8+
- Chave da Google Maps Platform com as APIs abaixo habilitadas:
  - Maps JavaScript API
  - Places API
  - Solar API

---

## 🚀 Instalação

### 1. Clone o repositório

```bash
git clone https://github.com/viniciussilva-dev/prospeccao-usinas-solares-sp.git
cd prospeccao-usinas-solares-sp
```

### 2. Instale as dependências Python

```bash
pip install -r requirements.txt
```

### 3. Configure as variáveis de ambiente

```bash
cp .env.example .env
```

Edite o `.env` com suas credenciais:

```env
# Chave da Google Maps Platform
GOOGLE_MAPS_API_KEY=sua_chave_aqui

# Banco de dados MySQL
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=nome_do_banco
DB_USER=seu_usuario
DB_PASSWORD=sua_senha
```

### 4. Configure a chave no frontend

Em `frontend/index.html`, substitua `SUA_CHAVE_AQUI` pela sua chave real:

```html
<script src="https://maps.googleapis.com/maps/api/js?key=SUA_CHAVE_AQUI&callback=iniciarMapa" async defer></script>
```

---

## 📥 Gerando os dados

Execute os scripts em ordem. Cada um depende do anterior.

### Passo 1 — Filtrar usinas da ANEEL

```bash
python python/1_filtrar_aneel.py
```

Acessa a API pública da ANEEL, filtra `UFV + SP + ≥300kW` e salva em `dados/filtrado_sp.csv`.

### Passo 2 — Consultar Google Maps

```bash
python python/2_consultar_maps.py
```

Para cada usina, busca nome, telefone, endereço e site via Google Maps Places API. Processa em lotes de 20 com cache SQLite para evitar cobranças duplicadas. Salva em `resultados/lista_vendas.csv`.

### Passo 3 — Consultar Solar API

```bash
python python/3_solar_api.py
```

Para cada usina, analisa o telhado via satélite e calcula o potencial de expansão. Também usa cache SQLite. Salva em `resultados/lista_vendas_solar.csv` ordenado pelo maior potencial de expansão.

---

## 🖥️ Rodando o sistema

### Backend

```bash
cd backend
python app.py
```

O servidor sobe em `http://localhost:5001`. Confirme acessando `http://localhost:5001/health`.

### Frontend

Em outro terminal:

```bash
cd frontend
python -m http.server 3000
```

Acesse `http://localhost:3000` no navegador.

> ⚠️ Não abra o `index.html` diretamente como arquivo — o navegador bloqueará o carregamento dos CSVs por política de segurança. Use sempre o servidor HTTP.

---

## 💾 Sistema de cache

Os scripts 2 e 3 usam um banco SQLite em `cache/cache.db` com duas tabelas:

```
cache_maps   → resultados do Google Maps Places
cache_solar  → resultados da Google Solar API
```

**Benefícios:**
- Se o script for interrompido, retoma de onde parou
- Nas próximas execuções, reutiliza resultados já consultados
- Zero custo adicional para coordenadas já processadas

---

## 💰 Custo estimado das APIs

| API | Consultas | Custo estimado |
|---|---|---|
| Maps Nearby Search | 779 | ~US$ 24,93 |
| Maps Place Details | 779 | ~US$ 13,24 |
| Solar API | 779 | ~US$ 7,80 |
| **Total** | **2.337** | **~US$ 46,00** |

O Google oferece **US$ 200,00 de crédito gratuito por mês** — o projeto roda inteiro dentro do gratuito.

---

## 🔌 API do backend

| Método | Endpoint | Descrição |
|---|---|---|
| GET | `/health` | Verifica se o servidor está rodando |
| GET | `/api/status` | Retorna todos os status salvos |
| POST | `/api/status` | Salva ou atualiza o status de uma usina |
| GET | `/api/status/<chave>` | Retorna o status de uma usina específica |
| GET | `/api/resumo` | Contagem de usinas por status |

---

## 🛠️ Tecnologias

| Camada | Tecnologia |
|---|---|
| Scripts de dados | Python 3.11, Pandas, Requests, SQLite |
| Frontend | HTML5, CSS3, JavaScript vanilla, PapaParse |
| Mapa | Google Maps JavaScript API |
| Backend | Python, Flask, Flask-CORS |
| Banco de dados | MySQL 8 |
| APIs externas | Google Maps Places API, Google Solar API, ANEEL Dados Abertos |

---

## 📄 Fonte dos dados

[ANEEL — Relação de Empreendimentos de Geração Distribuída](https://dadosabertos.aneel.gov.br/dataset/relacao-de-empreendimentos-de-geracao-distribuida)

Dados públicos do governo brasileiro. Atualização mensal.

---

## 👤 Autor

Desenvolvido por Vinicius Silva.
