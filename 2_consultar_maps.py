# === IMPORTS ===
import pandas as pd          # Para ler o CSV filtrado da ANEEL
import requests              # Para chamar a API do Google Maps
import os                    # Para criar pastas e verificar arquivos
import json                  # Para salvar e ler o cache
import time                  # Para pausa entre lotes
from dotenv import load_dotenv  # Para ler a chave do arquivo .env

# === CARREGA A CHAVE DA API DO ARQUIVO .env ===
# Por que usar .env? Para não expor a chave no código
load_dotenv()
API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

if not API_KEY:
    raise ValueError("❌ Chave do Google Maps não encontrada! Verifique o arquivo .env")

# === CONFIGURAÇÕES ===
ARQUIVO_ENTRADA = os.path.join("dados", "filtrado_sp.csv")
ARQUIVO_CACHE   = os.path.join("cache", "cache_maps.json")
ARQUIVO_SAIDA   = os.path.join("resultados", "lista_vendas.csv")

TAMANHO_LOTE = 20    # Consulta 20 usinas por vez
PAUSA_LOTE   = 2     # Segundos de pausa entre lotes

# Colunas de coordenadas no CSV da ANEEL
COL_LAT = "NumCoordNEmpreendimento"
COL_LNG = "NumCoordEEmpreendimento"
COL_POT = "MdaPotenciaInstaladaKW"
COL_MUN = "NomMunicipio"
COL_TIT = "NomTitularEmpreendimento"


# === FUNÇÃO: CRIAR PASTAS ===
def criar_pastas():
    """Cria as pastas necessárias se não existirem"""
    os.makedirs("cache", exist_ok=True)
    os.makedirs("resultados", exist_ok=True)
    print("✅ Pastas verificadas")


# === FUNÇÃO: CARREGAR CACHE ===
def carregar_cache():
    """
    Carrega o cache de consultas já feitas.
    Evita gastar API para coordenadas já consultadas.
    """
    if os.path.exists(ARQUIVO_CACHE):
        with open(ARQUIVO_CACHE, "r", encoding="utf-8") as f:
            cache = json.load(f)
        print(f"✅ Cache carregado: {len(cache)} consultas já realizadas")
        return cache
    else:
        print("ℹ️  Nenhum cache encontrado — começando do zero")
        return {}


# === FUNÇÃO: SALVAR CACHE ===
def salvar_cache(cache):
    """Salva o cache em disco após cada lote para não perder progresso"""
    with open(ARQUIVO_CACHE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


# === FUNÇÃO: FORMATAR COORDENADA ===
def formatar_coord(valor):
    """
    Converte a coordenada do formato brasileiro para o formato da API.
    CSV da ANEEL usa vírgula: -23,53
    API do Google Maps precisa de ponto: -23.53
    """
    # Verifica se o valor é nulo
    if pd.isna(valor):
        return None

    # Converte para string, substitui vírgula por ponto, remove espaços
    valor_str = str(valor).replace(",", ".").strip().replace(" ", "")

    # Verifica se é um número válido antes de retornar
    try:
        float(valor_str)
        return valor_str
    except ValueError:
        # Se não conseguir converter para número, retorna None
        return None


# === FUNÇÃO: CONSULTAR GOOGLE MAPS ===
def consultar_maps(lat, lng):
    """
    Consulta a API Nearby Search do Google Maps para uma coordenada.
    Retorna o estabelecimento mais próximo com seus dados.
    """
    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"

    params = {
        "location": f"{lat},{lng}",  # Coordenada da usina
        "radius": 50,                # Raio de 50 metros
        "key": API_KEY
    }

    try:
        resposta = requests.get(url, params=params, timeout=10)
        resposta.raise_for_status()
        dados = resposta.json()

        if dados.get("status") == "OK" and dados.get("results"):
            lugar = dados["results"][0]
            place_id = lugar.get("place_id")
            detalhes = buscar_detalhes(place_id)
            return detalhes

        elif dados.get("status") == "ZERO_RESULTS":
            return {"nome": "Não encontrado", "telefone": "", "endereco": "", "site": ""}

        else:
            print(f"      ⚠️  Status da API: {dados.get('status')}")
            return None

    except Exception as e:
        print(f"      ❌ Erro na consulta: {e}")
        return None


# === FUNÇÃO: BUSCAR DETALHES DO LUGAR ===
def buscar_detalhes(place_id):
    """
    Busca detalhes completos de um lugar pelo place_id.
    Retorna telefone, endereço e site do estabelecimento.
    """
    url = "https://maps.googleapis.com/maps/api/place/details/json"

    params = {
        "place_id": place_id,
        "fields": "name,formatted_phone_number,formatted_address,website",
        "key": API_KEY,
        "language": "pt-BR"
    }

    try:
        resposta = requests.get(url, params=params, timeout=10)
        resposta.raise_for_status()
        dados = resposta.json()

        if dados.get("status") == "OK":
            resultado = dados.get("result", {})
            return {
                "nome":     resultado.get("name", ""),
                "telefone": resultado.get("formatted_phone_number", ""),
                "endereco": resultado.get("formatted_address", ""),
                "site":     resultado.get("website", "")
            }
        else:
            return {"nome": "", "telefone": "", "endereco": "", "site": ""}

    except Exception as e:
        print(f"      ❌ Erro nos detalhes: {e}")
        return {"nome": "", "telefone": "", "endereco": "", "site": ""}


# === FUNÇÃO: PROCESSAR USINAS EM LOTES ===
def processar_usinas(df, cache):
    """
    Processa todas as usinas em lotes de 20.
    Verifica cache antes de cada consulta para não gastar API.
    """
    total = len(df)
    resultados = []
    consultadas_agora = 0
    coordenadas_invalidas = 0

    print(f"\n🗺️  Processando {total} usinas em lotes de {TAMANHO_LOTE}...")
    print(f"   Já no cache: {len(cache)} usinas (não serão cobradas)")
    print(f"   Estimativa de novas consultas: {total - len(cache)} chamadas à API\n")

    for i, (_, row) in enumerate(df.iterrows()):

        # --- Formata as coordenadas ---
        lat = formatar_coord(row.get(COL_LAT))
        lng = formatar_coord(row.get(COL_LNG))

        # --- Debug: mostra coordenadas inválidas ---
        # Isso nos ajuda a entender quais usinas não têm coordenada válida
        if lat is None or lng is None:
            coordenadas_invalidas += 1
            print(f"      ⚠️  Coordenada inválida [{i+1}]: "
                  f"LAT='{row.get(COL_LAT)}' LNG='{row.get(COL_LNG)}'")

        # --- Chave única para o cache ---
        chave_cache = f"{lat},{lng}"

        # --- Verifica se já está no cache ---
        if chave_cache in cache:
            # Usa resultado do cache — não gasta API!
            info_maps = cache[chave_cache]
            fonte = "cache"

        elif lat and lng and lat != "nan" and lng != "nan":
            # Coordenada válida — consulta o Google Maps
            info_maps = consultar_maps(lat, lng)

            if info_maps:
                # Salva no cache imediatamente após consultar
                cache[chave_cache] = info_maps
                consultadas_agora += 1
                fonte = "API"
            else:
                info_maps = {"nome": "Erro na consulta", "telefone": "", "endereco": "", "site": ""}
                fonte = "erro"

        else:
            # Coordenada inválida ou vazia
            info_maps = {"nome": "Sem coordenada", "telefone": "", "endereco": "", "site": ""}
            fonte = "sem coord"

        # --- Monta linha do resultado ---
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

        # --- Mostra progresso ---
        print(f"   [{i+1:3d}/{total}] {row.get(COL_MUN, ''):<22} "
              f"{str(row.get(COL_POT, '')):<8} kW | "
              f"{info_maps.get('nome', '')[:35]:<35} [{fonte}]")

        # --- Salva cache e pausa a cada lote de 20 ---
        if (i + 1) % TAMANHO_LOTE == 0:
            salvar_cache(cache)
            print(f"\n   💾 Cache salvo ({len(cache)} entradas) — "
                  f"pausando {PAUSA_LOTE}s...\n")
            time.sleep(PAUSA_LOTE)

    # Salva cache final
    salvar_cache(cache)

    print(f"\n✅ Processamento completo!")
    print(f"   Novas consultas à API: {consultadas_agora}")
    print(f"   Coordenadas inválidas: {coordenadas_invalidas}")
    print(f"   Total no cache: {len(cache)}")

    return pd.DataFrame(resultados)


# === FUNÇÃO: SALVAR LISTA FINAL ===
def salvar_lista(df_resultado):
    """Salva a lista final ordenada por potência (maior primeiro)"""
    df_resultado = df_resultado.sort_values("Potência (kW)", ascending=False)
    df_resultado.to_csv(ARQUIVO_SAIDA, index=False, encoding="utf-8-sig", sep=";")
    print(f"\n💾 Lista salva em: {ARQUIVO_SAIDA}")
    print(f"   Total de usinas na lista: {len(df_resultado)}")


# === FUNÇÃO: MOSTRAR RESUMO FINAL ===
def mostrar_resumo(df_resultado):
    """Mostra as primeiras usinas encontradas no terminal"""
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

    # Passo 1: Cria pastas necessárias
    criar_pastas()

    # Passo 2: Lê o CSV filtrado gerado pelo script 1
    print(f"\n📂 Lendo arquivo: {ARQUIVO_ENTRADA}")
    if not os.path.exists(ARQUIVO_ENTRADA):
        raise FileNotFoundError(f"❌ Arquivo não encontrado: {ARQUIVO_ENTRADA}\n"
                                f"   Execute primeiro o 1_filtrar_aneel.py!")

    df = pd.read_csv(ARQUIVO_ENTRADA, sep=";", encoding="utf-8-sig")
    print(f"✅ {len(df)} usinas carregadas")

    # Passo 3: Carrega cache de consultas anteriores
    cache = carregar_cache()

    # Passo 4: Processa as usinas consultando o Maps
    df_resultado = processar_usinas(df, cache)

    # Passo 5: Salva lista final
    salvar_lista(df_resultado)

    # Passo 6: Mostra resumo
    mostrar_resumo(df_resultado)

    print("\n✅ Tudo pronto! Abra o arquivo resultados/lista_vendas.csv")