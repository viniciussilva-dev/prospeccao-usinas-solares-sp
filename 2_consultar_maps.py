# === IMPORTS ===
import pandas as pd          # Para ler o CSV filtrado da ANEEL
import requests              # Para chamar a API do Google Maps
import os                    # Para criar pastas e verificar arquivos
import sqlite3               # Banco de dados local — já vem no Python
import time                  # Para pausa entre lotes
from dotenv import load_dotenv  # Para ler a chave do arquivo .env

# === CARREGA A CHAVE DA API ===
load_dotenv()
API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

if not API_KEY:
    raise ValueError("❌ Chave do Google Maps não encontrada! Verifique o arquivo .env")

# === CONFIGURAÇÕES ===
ARQUIVO_ENTRADA = os.path.join("dados", "filtrado_sp.csv")
ARQUIVO_DB      = os.path.join("cache", "cache.db")
ARQUIVO_SAIDA   = os.path.join("resultados", "lista_vendas.csv")

TAMANHO_LOTE = 20
PAUSA_LOTE   = 2

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
    Conecta ao banco SQLite e garante que a tabela existe.
    Por que SQLite? Mais rápido que JSON, suporta SQL, arquivo único.
    """
    conn = sqlite3.connect(ARQUIVO_DB)
    cursor = conn.cursor()

    # Cria tabela se não existir
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cache_maps (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            latitude    TEXT NOT NULL,
            longitude   TEXT NOT NULL,
            chave       TEXT UNIQUE NOT NULL,
            nome        TEXT,
            telefone    TEXT,
            endereco    TEXT,
            site        TEXT,
            criado_em   DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_maps_chave ON cache_maps(chave)")
    conn.commit()

    # Conta registros existentes
    cursor.execute("SELECT COUNT(*) FROM cache_maps")
    total = cursor.fetchone()[0]
    print(f"✅ Banco conectado: {total:,} consultas já realizadas")
    return conn


# === FUNÇÃO: BUSCAR NO CACHE ===
def buscar_cache(conn, chave):
    """Busca uma coordenada no banco. Retorna None se não encontrar."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT nome, telefone, endereco, site
        FROM cache_maps WHERE chave = ?
    """, (chave,))
    row = cursor.fetchone()
    if row:
        return {"nome": row[0], "telefone": row[1], "endereco": row[2], "site": row[3]}
    return None


# === FUNÇÃO: SALVAR NO CACHE ===
def salvar_cache(conn, chave, lat, lng, dados):
    """Salva resultado no banco imediatamente após consultar."""
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO cache_maps
            (latitude, longitude, chave, nome, telefone, endereco, site)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (lat, lng, chave,
          dados.get("nome", ""),
          dados.get("telefone", ""),
          dados.get("endereco", ""),
          dados.get("site", "")))
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


# === FUNÇÃO: CONSULTAR GOOGLE MAPS ===
def consultar_maps(lat, lng):
    """Consulta Nearby Search para encontrar o estabelecimento na coordenada."""
    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {"location": f"{lat},{lng}", "radius": 50, "key": API_KEY}

    try:
        resposta = requests.get(url, params=params, timeout=10)
        resposta.raise_for_status()
        dados = resposta.json()

        if dados.get("status") == "OK" and dados.get("results"):
            place_id = dados["results"][0].get("place_id")
            return buscar_detalhes(place_id)
        elif dados.get("status") == "ZERO_RESULTS":
            return {"nome": "Não encontrado", "telefone": "", "endereco": "", "site": ""}
        else:
            print(f"      ⚠️  Status: {dados.get('status')}")
            return None
    except Exception as e:
        print(f"      ❌ Erro: {e}")
        return None


# === FUNÇÃO: BUSCAR DETALHES DO LUGAR ===
def buscar_detalhes(place_id):
    """Busca telefone, endereço e site pelo place_id."""
    url = "https://maps.googleapis.com/maps/api/place/details/json"
    params = {
        "place_id": place_id,
        "fields": "name,formatted_phone_number,formatted_address,website",
        "key": API_KEY,
        "language": "pt-BR"
    }
    try:
        resposta = requests.get(url, params=params, timeout=10)
        dados = resposta.json()
        if dados.get("status") == "OK":
            r = dados.get("result", {})
            return {
                "nome":     r.get("name", ""),
                "telefone": r.get("formatted_phone_number", ""),
                "endereco": r.get("formatted_address", ""),
                "site":     r.get("website", "")
            }
        return {"nome": "", "telefone": "", "endereco": "", "site": ""}
    except Exception as e:
        print(f"      ❌ Erro nos detalhes: {e}")
        return {"nome": "", "telefone": "", "endereco": "", "site": ""}


# === FUNÇÃO: PROCESSAR USINAS ===
def processar_usinas(df, conn):
    """Processa todas as usinas em lotes de 20 usando SQLite como cache."""
    total = len(df)
    resultados = []
    consultadas_agora = 0

    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM cache_maps")
    total_cache = cursor.fetchone()[0]

    print(f"\n🗺️  Processando {total} usinas em lotes de {TAMANHO_LOTE}...")
    print(f"   Já no banco: {total_cache:,} usinas (não serão cobradas)\n")

    for i, (_, row) in enumerate(df.iterrows()):

        lat = formatar_coord(row.get(COL_LAT))
        lng = formatar_coord(row.get(COL_LNG))
        chave = f"{lat},{lng}"

        # Verifica cache no banco SQLite
        cached = buscar_cache(conn, chave)

        if cached:
            info_maps = cached
            fonte = "banco"

        elif lat and lng and lat != "nan" and lng != "nan":
            info_maps = consultar_maps(lat, lng)
            if info_maps:
                salvar_cache(conn, chave, lat, lng, info_maps)
                consultadas_agora += 1
                fonte = "API"
            else:
                info_maps = {"nome": "Erro na consulta", "telefone": "", "endereco": "", "site": ""}
                fonte = "erro"
        else:
            info_maps = {"nome": "Sem coordenada", "telefone": "", "endereco": "", "site": ""}
            fonte = "sem coord"

        resultados.append({
            "Titular ANEEL":  row.get(COL_TIT, ""),
            "Município":      row.get(COL_MUN, ""),
            "Potência (kW)":  row.get(COL_POT, ""),
            "Nome no Maps":   info_maps.get("nome", ""),
            "Telefone":       info_maps.get("telefone", ""),
            "Endereço":       info_maps.get("endereco", ""),
            "Site":           info_maps.get("site", ""),
            "Latitude":       lat,
            "Longitude":      lng,
            "Fonte":          fonte
        })

        print(f"   [{i+1:3d}/{total}] {row.get(COL_MUN, ''):<22} "
              f"{str(row.get(COL_POT, '')):<8} kW | "
              f"{info_maps.get('nome', '')[:35]:<35} [{fonte}]")

        if (i + 1) % TAMANHO_LOTE == 0:
            cursor.execute("SELECT COUNT(*) FROM cache_maps")
            total_banco = cursor.fetchone()[0]
            print(f"\n   💾 Banco salvo ({total_banco:,} entradas) — pausando {PAUSA_LOTE}s...\n")
            time.sleep(PAUSA_LOTE)

    print(f"\n✅ Processamento completo!")
    print(f"   Novas consultas à API: {consultadas_agora}")
    return pd.DataFrame(resultados)


# === FUNÇÃO: SALVAR LISTA FINAL ===
def salvar_lista(df_resultado):
    df_resultado = df_resultado.sort_values("Potência (kW)", ascending=False)
    df_resultado.to_csv(ARQUIVO_SAIDA, index=False, encoding="utf-8-sig", sep=";")
    print(f"\n💾 Lista salva em: {ARQUIVO_SAIDA}")
    print(f"   Total de usinas: {len(df_resultado)}")


# === FUNÇÃO: MOSTRAR RESUMO ===
def mostrar_resumo(df_resultado):
    print(f"\n{'='*70}")
    print(f"📋 LISTA PARA VENDEDORES — TOP 10 MAIORES USINAS")
    print(f"{'='*70}")
    colunas = ["Município", "Potência (kW)", "Nome no Maps", "Telefone", "Endereço"]
    print(df_resultado[colunas].head(10).to_string(index=False))
    print(f"{'='*70}")


# === EXECUÇÃO PRINCIPAL ===
if __name__ == "__main__":
    print("🗺️  CONSULTOR DE USINAS — GOOGLE MAPS")
    print("=" * 70)

    criar_pastas()

    print(f"\n📂 Lendo arquivo: {ARQUIVO_ENTRADA}")
    if not os.path.exists(ARQUIVO_ENTRADA):
        raise FileNotFoundError(f"❌ Execute primeiro o 1_filtrar_aneel.py!")

    df = pd.read_csv(ARQUIVO_ENTRADA, sep=";", encoding="utf-8-sig")
    print(f"✅ {len(df)} usinas carregadas")

    conn = conectar_banco()
    df_resultado = processar_usinas(df, conn)
    conn.close()

    salvar_lista(df_resultado)
    mostrar_resumo(df_resultado)

    print("\n✅ Tudo pronto! Abra o arquivo resultados/lista_vendas.csv")