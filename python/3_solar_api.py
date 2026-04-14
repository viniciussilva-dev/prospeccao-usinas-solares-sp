# === IMPORTS ===
import pandas as pd          # Para ler o CSV filtrado da ANEEL
import requests              # Para chamar a Google Solar API
import os                    # Para criar pastas e verificar arquivos
import sqlite3               # Banco de dados local — já vem no Python
import time                  # Para pausa entre lotes
from dotenv import load_dotenv  # Para ler a chave do arquivo .env

# === CARREGA A CHAVE DA API ===
# A mesma chave do Google Maps serve para a Solar API
load_dotenv()
API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

if not API_KEY:
    raise ValueError("❌ Chave não encontrada! Verifique o arquivo .env")

# === CONFIGURAÇÕES ===
ARQUIVO_ENTRADA  = os.path.join("dados", "filtrado_sp.csv")
ARQUIVO_DB       = os.path.join("cache", "cache.db")
ARQUIVO_SAIDA    = os.path.join("resultados", "lista_vendas_solar.csv")

# Capacidade de um painel solar padrão em kW
# Usado para calcular potência máxima possível
CAPACIDADE_PAINEL_KW = 0.4  # 400W por painel — padrão do mercado

TAMANHO_LOTE = 20   # Processa 20 usinas por vez
PAUSA_LOTE   = 2    # Segundos de pausa entre lotes

# Colunas do CSV da ANEEL
COL_LAT = "NumCoordNEmpreendimento"
COL_LNG = "NumCoordEEmpreendimento"
COL_POT = "MdaPotenciaInstaladaKW"
COL_MUN = "NomMunicipio"
COL_TIT = "NomTitularEmpreendimento"


# === FUNÇÃO: CRIAR PASTAS ===
def criar_pastas():
    os.makedirs("cache", exist_ok=True)
    os.makedirs("resultados", exist_ok=True)
    print("✅ Pastas verificadas")


# === FUNÇÃO: CONECTAR AO BANCO ===
def conectar_banco():
    """
    Conecta ao banco SQLite e garante que a tabela cache_solar existe.
    A tabela cache_maps já existe desde o script 2.
    """
    conn = sqlite3.connect(ARQUIVO_DB)
    cursor = conn.cursor()

    # Cria tabela cache_solar se não existir
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cache_solar (
            id                      INTEGER PRIMARY KEY AUTOINCREMENT,
            latitude                TEXT NOT NULL,
            longitude               TEXT NOT NULL,
            chave                   TEXT UNIQUE NOT NULL,  -- "lat,lng"
            area_telhado_m2         REAL,    -- Área total do telhado em m²
            max_paineis             INTEGER, -- Máximo de painéis que cabem
            horas_sol_ano           REAL,    -- Horas de sol por ano
            potencia_maxima_kw      REAL,    -- Potência máxima possível em kW
            potencia_instalada_kw   REAL,    -- Potência já instalada (da ANEEL)
            potencial_expansao_kw   REAL,    -- Quanto ainda pode instalar
            economia_anual_usd      REAL,    -- Economia estimada por ano em USD
            offset_carbono          REAL,    -- Redução de CO2 kg/MWh
            qualidade_imagem        TEXT,    -- Qualidade da imagem (HIGH/MEDIUM/LOW)
            criado_em               DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Índice para busca rápida
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_solar_chave ON cache_solar(chave)
    """)
    conn.commit()

    # Mostra quantos registros já existem no cache solar
    cursor.execute("SELECT COUNT(*) FROM cache_solar")
    total = cursor.fetchone()[0]
    print(f"✅ Banco conectado: {total:,} consultas solares já realizadas")
    return conn


# === FUNÇÃO: BUSCAR NO CACHE SOLAR ===
def buscar_cache_solar(conn, chave):
    """
    Busca resultado solar no banco pelo par lat,lng.
    Retorna None se não encontrar — significa que precisa consultar a API.
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT area_telhado_m2, max_paineis, horas_sol_ano,
               potencia_maxima_kw, potencia_instalada_kw,
               potencial_expansao_kw, economia_anual_usd,
               offset_carbono, qualidade_imagem
        FROM cache_solar WHERE chave = ?
    """, (chave,))
    row = cursor.fetchone()
    if row:
        return {
            "area_telhado_m2":       row[0],
            "max_paineis":           row[1],
            "horas_sol_ano":         row[2],
            "potencia_maxima_kw":    row[3],
            "potencia_instalada_kw": row[4],
            "potencial_expansao_kw": row[5],
            "economia_anual_usd":    row[6],
            "offset_carbono":        row[7],
            "qualidade_imagem":      row[8]
        }
    return None


# === FUNÇÃO: SALVAR NO CACHE SOLAR ===
def salvar_cache_solar(conn, chave, lat, lng, dados):
    """
    Salva resultado da Solar API no banco imediatamente.
    OR IGNORE evita erro se a chave já existir.
    """
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO cache_solar (
            latitude, longitude, chave,
            area_telhado_m2, max_paineis, horas_sol_ano,
            potencia_maxima_kw, potencia_instalada_kw,
            potencial_expansao_kw, economia_anual_usd,
            offset_carbono, qualidade_imagem
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        lat, lng, chave,
        dados.get("area_telhado_m2"),
        dados.get("max_paineis"),
        dados.get("horas_sol_ano"),
        dados.get("potencia_maxima_kw"),
        dados.get("potencia_instalada_kw"),
        dados.get("potencial_expansao_kw"),
        dados.get("economia_anual_usd"),
        dados.get("offset_carbono"),
        dados.get("qualidade_imagem")
    ))
    conn.commit()


# === FUNÇÃO: FORMATAR COORDENADA ===
def formatar_coord(valor):
    """Converte coordenada do formato brasileiro (-23,53) para (-23.53)"""
    if pd.isna(valor):
        return None
    valor_str = str(valor).replace(",", ".").strip().replace(" ", "")
    try:
        float(valor_str)
        return valor_str
    except ValueError:
        return None


# === FUNÇÃO: CONSULTAR SOLAR API ===
def consultar_solar(lat, lng, potencia_instalada_kw):
    """
    Consulta a Google Solar API para uma coordenada.

    Endpoint usado: buildingInsights:findClosest
    Ele retorna dados do edifício mais próximo à coordenada.

    Por que esse endpoint?
    É o mais simples e direto — dado um ponto (lat/lng),
    retorna tudo sobre o potencial solar do telhado.
    """
    url = "https://solar.googleapis.com/v1/buildingInsights:findClosest"

    params = {
        "location.latitude":  lat,
        "location.longitude": lng,
        "requiredQuality":    "LOW",  # LOW aceita imagens de qualquer qualidade
        "key":                API_KEY
    }

    try:
        resposta = requests.get(url, params=params, timeout=15)
        resposta.raise_for_status()
        dados = resposta.json()

        # Verifica se retornou erro
        if "error" in dados:
            codigo = dados["error"].get("code")
            mensagem = dados["error"].get("message", "")

            # NOT_FOUND = não tem dados para essa coordenada (não cobra)
            if codigo == 404:
                return {"erro": "Sem dados solares para essa localização"}

            print(f"      ⚠️  Erro Solar API: {codigo} — {mensagem}")
            return None

        # === EXTRAI OS DADOS DO TELHADO ===
        solar = dados.get("solarPotential", {})

        # Área total do telhado disponível
        area_m2 = solar.get("wholeRoofStats", {}).get("areaMeters2", 0)

        # Máximo de painéis que cabem no telhado
        max_paineis = solar.get("maxArrayPanelsCount", 0)

        # Horas de sol por ano
        horas_sol = solar.get("maxSunshineHoursPerYear", 0)

        # Potência máxima possível com todos os painéis
        # Cada painel = 400W = 0.4kW
        potencia_maxima_kw = round(max_paineis * CAPACIDADE_PAINEL_KW, 2)

        # Potencial de expansão = quanto ainda pode instalar
        # Se o telhado comporta 800kW e já tem 500kW → expansão = 300kW
        potencial_expansao_kw = round(
            max(0, potencia_maxima_kw - float(potencia_instalada_kw or 0)), 2
        )

        # Fator de offset de carbono
        offset_carbono = solar.get("carbonOffsetFactorKgPerMwh", 0)

        # Qualidade da imagem retornada
        qualidade = dados.get("imageryQuality", "UNKNOWN")

        # Economia anual estimada — pega da análise financeira se disponível
        economia_anual = 0
        configs = solar.get("solarPanelConfigs", [])
        if configs:
            # Pega a configuração com mais painéis (maior economia)
            melhor_config = configs[-1]
            analises = melhor_config.get("financialAnalyses", [])
            if analises:
                savings = analises[0].get("cashPurchaseSavings", {})
                economia_anual = savings.get("savings", {}).get("savingsYear1", {}).get("units", 0)

        return {
            "area_telhado_m2":       round(area_m2, 2),
            "max_paineis":           max_paineis,
            "horas_sol_ano":         round(horas_sol, 1),
            "potencia_maxima_kw":    potencia_maxima_kw,
            "potencia_instalada_kw": float(potencia_instalada_kw or 0),
            "potencial_expansao_kw": potencial_expansao_kw,
            "economia_anual_usd":    float(economia_anual or 0),
            "offset_carbono":        round(offset_carbono, 2),
            "qualidade_imagem":      qualidade
        }

    except requests.exceptions.Timeout:
        print(f"      ⚠️  Timeout — tentando novamente...")
        time.sleep(3)
        return consultar_solar(lat, lng, potencia_instalada_kw)

    except Exception as e:
        print(f"      ❌ Erro: {e}")
        return None


# === FUNÇÃO: BUSCAR DADOS DO MAPS NO BANCO ===
def buscar_dados_maps(conn, chave):
    """
    Busca os dados do Google Maps (nome, telefone) já salvos no banco.
    Assim cruzamos os dados do Maps com os dados solares na lista final.
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT nome, telefone, endereco, site
        FROM cache_maps WHERE chave = ?
    """, (chave,))
    row = cursor.fetchone()
    if row:
        return {"nome": row[0], "telefone": row[1], "endereco": row[2], "site": row[3]}
    return {"nome": "", "telefone": "", "endereco": "", "site": ""}


# === FUNÇÃO: PROCESSAR USINAS ===
def processar_usinas(df, conn):
    """
    Processa todas as usinas consultando a Solar API.
    Cruza com os dados do Maps já salvos no banco.
    Salva tudo no banco a cada consulta.
    """
    total = len(df)
    resultados = []
    consultadas_agora = 0
    sem_dados = 0

    print(f"\n☀️  Processando {total} usinas com Solar API...")
    print(f"   Lote de {TAMANHO_LOTE} por vez | Pausa de {PAUSA_LOTE}s entre lotes\n")

    for i, (_, row) in enumerate(df.iterrows()):

        # Formata coordenadas
        lat = formatar_coord(row.get(COL_LAT))
        lng = formatar_coord(row.get(COL_LNG))
        chave = f"{lat},{lng}"
        potencia_instalada = row.get(COL_POT, 0)

        # Busca dados do Maps já salvos (nome, telefone)
        dados_maps = buscar_dados_maps(conn, chave)

        # Verifica cache solar no banco
        cached_solar = buscar_cache_solar(conn, chave)

        if cached_solar:
            dados_solar = cached_solar
            fonte = "banco"

        elif lat and lng and lat != "nan" and lng != "nan":
            # Consulta a Solar API
            dados_solar = consultar_solar(lat, lng, potencia_instalada)

            if dados_solar and "erro" not in dados_solar:
                salvar_cache_solar(conn, chave, lat, lng, dados_solar)
                consultadas_agora += 1
                fonte = "API"
            elif dados_solar and "erro" in dados_solar:
                dados_solar = {}
                sem_dados += 1
                fonte = "sem dados"
            else:
                dados_solar = {}
                fonte = "erro"
        else:
            dados_solar = {}
            fonte = "sem coord"

        # Monta linha do resultado final
        # Cruza dados da ANEEL + Google Maps + Solar API
        resultados.append({
            # === Dados da ANEEL ===
            "Titular ANEEL":        row.get(COL_TIT, ""),
            "Município":            row.get(COL_MUN, ""),
            "Potência Instalada kW": potencia_instalada,

            # === Dados do Google Maps (script 2) ===
            "Nome no Maps":         dados_maps.get("nome", ""),
            "Telefone":             dados_maps.get("telefone", ""),
            "Endereço":             dados_maps.get("endereco", ""),
            "Site":                 dados_maps.get("site", ""),

            # === Dados da Solar API (script 3) ===
            "Área Telhado m²":      dados_solar.get("area_telhado_m2", ""),
            "Máx Painéis":          dados_solar.get("max_paineis", ""),
            "Horas Sol/Ano":        dados_solar.get("horas_sol_ano", ""),
            "Potência Máx kW":      dados_solar.get("potencia_maxima_kw", ""),
            "Potencial Expansão kW": dados_solar.get("potencial_expansao_kw", ""),
            "Economia Anual USD":   dados_solar.get("economia_anual_usd", ""),
            "Offset Carbono kg/MWh": dados_solar.get("offset_carbono", ""),
            "Qualidade Imagem":     dados_solar.get("qualidade_imagem", ""),

            # === Metadados ===
            "Latitude":             lat,
            "Longitude":            lng,
            "Fonte Solar":          fonte
        })

        # Mostra progresso
        expansao = dados_solar.get("potencial_expansao_kw", "")
        expansao_str = f"+{expansao}kW" if expansao else "sem dados"
        print(f"   [{i+1:3d}/{total}] {row.get(COL_MUN, ''):<20} "
              f"{str(potencia_instalada):<8} kW instalado | "
              f"expansão: {expansao_str:<12} [{fonte}]")

        # Pausa a cada lote de 20
        if (i + 1) % TAMANHO_LOTE == 0:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM cache_solar")
            total_banco = cursor.fetchone()[0]
            print(f"\n   💾 Banco salvo ({total_banco:,} entradas solares) — "
                  f"pausando {PAUSA_LOTE}s...\n")
            time.sleep(PAUSA_LOTE)

    print(f"\n✅ Processamento completo!")
    print(f"   Novas consultas à Solar API: {consultadas_agora}")
    print(f"   Sem dados solares disponíveis: {sem_dados}")
    return pd.DataFrame(resultados)


# === FUNÇÃO: SALVAR LISTA FINAL ===
def salvar_lista(df_resultado):
    """Salva lista ordenada por potencial de expansão — maior oportunidade primeiro"""
    df_resultado["Potencial Expansão kW"] = pd.to_numeric(
    df_resultado["Potencial Expansão kW"], errors="coerce"
)
    df_resultado = df_resultado.sort_values(
    "Potencial Expansão kW",
    ascending=False,
    na_position="last"
)
    df_resultado.to_csv(ARQUIVO_SAIDA, index=False, encoding="utf-8-sig", sep=";")
    print(f"\n💾 Lista salva em: {ARQUIVO_SAIDA}")
    print(f"   Total de usinas: {len(df_resultado)}")


# === FUNÇÃO: MOSTRAR RESUMO ===
def mostrar_resumo(df_resultado):
    """Mostra top 10 usinas com maior potencial de expansão"""
    print(f"\n{'='*75}")
    print(f"☀️  TOP 10 USINAS COM MAIOR POTENCIAL DE EXPANSÃO")
    print(f"{'='*75}")

    colunas = ["Município", "Potência Instalada kW",
               "Potência Máx kW", "Potencial Expansão kW", "Telefone"]
    df_validos = df_resultado[df_resultado["Potencial Expansão kW"] != ""]
    if not df_validos.empty:
        print(df_validos[colunas].head(10).to_string(index=False))
    else:
        print("  Nenhum dado solar disponível ainda.")
    print(f"{'='*75}")


# === EXECUÇÃO PRINCIPAL ===
if __name__ == "__main__":
    print("☀️  SOLAR API — POTENCIAL DE EXPANSÃO DAS USINAS")
    print("=" * 75)

    # Passo 1: Cria pastas
    criar_pastas()

    # Passo 2: Lê CSV filtrado
    print(f"\n📂 Lendo arquivo: {ARQUIVO_ENTRADA}")
    if not os.path.exists(ARQUIVO_ENTRADA):
        raise FileNotFoundError("❌ Execute primeiro o 1_filtrar_aneel.py!")

    df = pd.read_csv(ARQUIVO_ENTRADA, sep=";", encoding="utf-8-sig")
    print(f"✅ {len(df)} usinas carregadas")

    # Passo 3: Conecta ao banco
    conn = conectar_banco()

    # Passo 4: Processa usinas com Solar API
    df_resultado = processar_usinas(df, conn)
    conn.close()

    # Passo 5: Salva lista final
    salvar_lista(df_resultado)

    # Passo 6: Mostra resumo
    mostrar_resumo(df_resultado)

    print("\n✅ Tudo pronto! Abra o arquivo resultados/lista_vendas_solar.csv")