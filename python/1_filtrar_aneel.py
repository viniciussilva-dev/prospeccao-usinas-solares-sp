# === IMPORTS ===
import pandas as pd       # Para manipular tabelas de dados
import requests           # Para fazer chamadas à API
import os                 # Para criar pastas
import time               # Para dar pausa entre requisições (não sobrecarregar o servidor)

# === CONFIGURAÇÕES ===
# ID do recurso CSV na API do CKAN da ANEEL
# Esse ID foi extraído da URL que você copiou do botão "Baixar CSV"
RESOURCE_ID = "b1bd71e7-d0ad-4214-9053-cbd58e9564a7"

# URL base da API CKAN — usamos o endpoint "datastore_search" que permite filtros
API_URL = f"https://dadosabertos.aneel.gov.br/api/3/action/datastore_search"

# Filtros
FILTRO_TIPO_GERACAO = "UFV"    # UFV = Usina Fotovoltaica
FILTRO_POTENCIA_MIN = 300      # kW mínimo
FILTRO_UF = "SP"               # Estado padrão

# Quantos registros buscar por requisição
# 1000 é o máximo seguro da API CKAN sem timeout
LOTE = 1000

# Caminhos de saída
PASTA_DADOS = "dados"
ARQUIVO_SAIDA = os.path.join(PASTA_DADOS, "filtrado_sp.csv")


# === FUNÇÃO: CRIAR PASTAS ===
def criar_estrutura_pastas():
    """Cria as pastas do projeto se ainda não existirem"""
    os.makedirs("dados", exist_ok=True)
    os.makedirs("resultados", exist_ok=True)
    print("✅ Pastas criadas/verificadas")


# === FUNÇÃO: BUSCAR UM LOTE DA API ===
def buscar_lote(offset):
    """
    Busca um lote de registros da API CKAN com filtros aplicados.
    
    Por que usamos a API com filtros em vez de baixar tudo?
    - O arquivo completo tem 4 milhões de registros e causa timeout
    - A API permite filtrar direto no servidor, trazendo só o que precisamos
    - Cada chamada traz 1000 registros — seguro e rápido
    
    offset = a partir de qual registro começar (0, 1000, 2000, ...)
    """
    # Parâmetros da requisição
    # filters = filtro exato por campo (tipo dicionário)
    # q = busca textual (não usamos aqui)
    params = {
        "resource_id": RESOURCE_ID,
        "limit": LOTE,           # Quantos registros trazer por vez
        "offset": offset,        # A partir de qual posição
        "filters": f'{{"SigTipoGeracao": "{FILTRO_TIPO_GERACAO}", "SigUF": "{FILTRO_UF}"}}'
        # Filtra UFV + SP direto na API — não precisamos baixar outros tipos
    }

    try:
        resposta = requests.get(API_URL, params=params, timeout=60)
        resposta.raise_for_status()
        dados = resposta.json()

        # A API CKAN retorna {"success": true, "result": {"records": [...], "total": N}}
        if not dados.get("success"):
            raise ValueError(f"API retornou erro: {dados.get('error')}")

        registros = dados["result"]["records"]
        total = dados["result"]["total"]  # Total de registros que batem o filtro
        return registros, total

    except requests.exceptions.Timeout:
        print(f"   ⚠️  Timeout no lote offset={offset}, tentando novamente...")
        time.sleep(5)  # Espera 5 segundos antes de tentar de novo
        return buscar_lote(offset)  # Tenta novamente (recursão simples)

    except Exception as e:
        print(f"   ❌ Erro no lote offset={offset}: {e}")
        raise


# === FUNÇÃO: BAIXAR TODOS OS REGISTROS EM LOTES ===
def baixar_dados_aneel():
    """
    Baixa todos os registros UFV + SP da API em lotes de 1000.
    Salva progresso parcial para não perder dados em caso de erro.
    
    Por que salvar progresso parcial?
    - Se cair a internet no meio, não perde o que já baixou
    - Evita ter que começar do zero
    """
    print(f"\n📥 Buscando dados da ANEEL via API (lotes de {LOTE})...")
    print(f"   Filtros ativos: Tipo={FILTRO_TIPO_GERACAO}, UF={FILTRO_UF}")

    todos_registros = []
    offset = 0

    # Primeira chamada para descobrir o total
    print(f"   Consultando total de registros...")
    registros, total = buscar_lote(0)
    todos_registros.extend(registros)

    print(f"   Total encontrado (UFV + SP): {total:,} registros")
    print(f"   Serão necessários {(total // LOTE) + 1} lotes de {LOTE}")

    # Loop para buscar os lotes restantes
    offset = LOTE
    while offset < total:
        print(f"   Baixando lote {offset//LOTE + 1}/{(total//LOTE) + 1} "
              f"(registros {offset} a {min(offset+LOTE, total)})...", end=" ")

        registros, _ = buscar_lote(offset)

        if not registros:
            # Se veio lista vazia, chegamos no fim
            break

        todos_registros.extend(registros)
        print(f"✅ ({len(todos_registros):,} acumulados)")

        offset += LOTE
        time.sleep(0.5)  # Pequena pausa para não sobrecarregar o servidor da ANEEL

    print(f"\n✅ Download completo: {len(todos_registros):,} registros UFV em SP")

    # Converte lista de dicionários em DataFrame
    df = pd.DataFrame(todos_registros)
    return df


# === FUNÇÃO: APLICAR FILTRO DE POTÊNCIA ===
def aplicar_filtro_potencia(df):
    """
    Aplica o filtro de potência >= 300kW.
    
    Por que não filtramos potência na API também?
    A API CKAN só suporta filtros de igualdade exata (ex: campo = "valor")
    Para filtros numéricos (>=, <=) precisamos fazer no pandas depois de baixar.
    """
    print(f"\n🔍 Aplicando filtro de potência ≥{FILTRO_POTENCIA_MIN}kW...")
    total_antes = len(df)

    # Mostra as colunas disponíveis para conferência
    print(f"   Colunas disponíveis ({len(df.columns)}):")
    cols = list(df.columns)
    for i in range(0, len(cols), 5):
        print(f"   {cols[i:i+5]}")

    # Identifica a coluna de potência (pode ter nome ligeiramente diferente)
    coluna_pot = None
    for col in df.columns:
        if "potencia" in col.lower() and "kw" in col.lower():
            coluna_pot = col
            break
        elif "potencia" in col.lower():
            coluna_pot = col  # Fallback se não tiver "kw" no nome

    if coluna_pot is None:
        print(f"   ⚠️  Coluna de potência não encontrada! Colunas disponíveis: {list(df.columns)}")
        return df

    print(f"   Usando coluna de potência: '{coluna_pot}'")

    # Converte para número (vírgula → ponto antes de converter)
    df = df.copy()
    df[coluna_pot] = pd.to_numeric(
        df[coluna_pot].astype(str).str.replace(",", "."),
        errors="coerce"  # Valores inválidos viram NaN em vez de quebrar
    )

    df_filtrado = df[df[coluna_pot] >= FILTRO_POTENCIA_MIN]
    print(f"   Após filtro ≥{FILTRO_POTENCIA_MIN}kW: {len(df_filtrado):,} "
          f"(removidos {total_antes - len(df_filtrado):,})")

    return df_filtrado, coluna_pot


# === FUNÇÃO: VERIFICAR COORDENADAS ===
def verificar_coordenadas(df):
    """Verifica quais colunas de localização estão disponíveis"""
    print(f"\n📍 Verificando colunas de localização...")

    colunas_loc = [col for col in df.columns if any(
        p in col.lower() for p in ["lat", "lon", "lng", "coord", "geo", "municipio", "nom", "end"]
    )]

    print(f"   Colunas de localização: {colunas_loc}")

    if colunas_loc:
        print(f"\n   Amostra (3 primeiras linhas):")
        print(df[colunas_loc].head(3).to_string())

    return colunas_loc


# === FUNÇÃO: SALVAR RESULTADO ===
def salvar_resultado(df):
    """Salva o CSV filtrado com encoding utf-8-sig (abre bem no Excel)"""
    df.to_csv(ARQUIVO_SAIDA, index=False, encoding="utf-8-sig", sep=";")
    print(f"\n💾 Arquivo salvo em: {ARQUIVO_SAIDA}")
    print(f"   Total de usinas para prospecção: {len(df):,}")


# === FUNÇÃO: MOSTRAR RESUMO ===
def mostrar_resumo(df, coluna_pot):
    """Mostra resumo final no terminal"""
    print(f"\n{'='*55}")
    print(f"📊 RESUMO FINAL")
    print(f"{'='*55}")
    print(f"  Usinas UFV ≥{FILTRO_POTENCIA_MIN}kW em {FILTRO_UF}: {len(df):,}")

    if coluna_pot and coluna_pot in df.columns:
        print(f"  Potência média : {df[coluna_pot].mean():.1f} kW")
        print(f"  Potência máxima: {df[coluna_pot].max():.1f} kW")
        print(f"  Potência mínima: {df[coluna_pot].min():.1f} kW")

    # Mostra colunas mais relevantes
    colunas_exibir = [c for c in ["NomEmpreendimento", "SigUF", "NomMunicipio",
                                   coluna_pot, "SigTipoGeracao"]
                      if c and c in df.columns]
    if colunas_exibir:
        print(f"\n  Primeiras 5 usinas encontradas:")
        print(df[colunas_exibir].head(5).to_string(index=False))
    print(f"{'='*55}")


# === EXECUÇÃO PRINCIPAL ===
if __name__ == "__main__":
    print("🌞 FILTRADOR DE USINAS FOTOVOLTAICAS — ANEEL")
    print("=" * 55)

    # Passo 1: Garante estrutura de pastas
    criar_estrutura_pastas()

    # Passo 2: Baixa dados via API (já com filtro UFV + SP)
    df_bruto = baixar_dados_aneel()

    # Passo 3: Aplica filtro de potência >= 300kW
    resultado = aplicar_filtro_potencia(df_bruto)
    if isinstance(resultado, tuple):
        df_filtrado, coluna_pot = resultado
    else:
        df_filtrado, coluna_pot = resultado, None

    # Passo 4: Mostra colunas de localização disponíveis
    verificar_coordenadas(df_filtrado)

    # Passo 5: Salva resultado
    salvar_resultado(df_filtrado)

    # Passo 6: Mostra resumo
    mostrar_resumo(df_filtrado, coluna_pot)

    print("\n✅ Pronto! Execute o 2_consultar_maps.py para o próximo passo.")