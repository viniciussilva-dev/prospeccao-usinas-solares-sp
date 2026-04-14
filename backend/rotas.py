# ================================================================
# ROTAS.PY — Endpoints da API REST
# Define o que acontece em cada URL do backend
# ================================================================

# === IMPORTS ===
from flask import Blueprint, request, jsonify  # Flask para criar rotas
from banco import obter_conexao                # Nossa função de conexão


# ================================================================
# BLUEPRINT — agrupa as rotas relacionadas ao status
# Permite organizar as rotas em arquivos separados
# ================================================================
rotas = Blueprint("rotas", __name__)


# ================================================================
# ROTA: GET /api/status
# Retorna todos os status salvos no banco
# O frontend chama essa rota ao abrir a página
# ================================================================
@rotas.route("/api/status", methods=["GET"])
def buscar_todos_status():
    """
    Retorna todos os registros de status como JSON.
    Formato: { "lat,lng": { status, vendedor, observacao, atualizado_em } }
    """
    try:
        conn = obter_conexao()
        cursor = conn.cursor(dictionary=True)
        # dictionary=True = retorna linhas como dicionários { coluna: valor }
        # sem isso retorna tuplas (valor1, valor2, ...)

        cursor.execute("""
            SELECT chave, status, vendedor, observacao,
                   DATE_FORMAT(atualizado_em, '%d/%m/%Y %H:%i') as atualizado_em
            FROM status_usinas
        """)
        # DATE_FORMAT = formata a data no padrão brasileiro dd/mm/aaaa hh:mm

        linhas = cursor.fetchall()
        # fetchall = busca todos os resultados da query

        # Converte a lista em dicionário indexado pela chave "lat,lng"
        # Isso facilita a busca no JavaScript
        resultado = {}
        for linha in linhas:
            chave = linha["chave"]
            resultado[chave] = {
                "status":       linha["status"],
                "vendedor":     linha["vendedor"] or "",
                "observacao":   linha["observacao"] or "",
                "atualizado_em": linha["atualizado_em"] or ""
            }

        return jsonify(resultado), 200
        # jsonify = converte dicionário Python para JSON
        # 200 = código HTTP de sucesso

    except Exception as e:
        print(f"❌ Erro ao buscar status: {e}")
        return jsonify({"erro": str(e)}), 500
        # 500 = código HTTP de erro interno do servidor

    finally:
        if cursor: cursor.close()
        if conn: conn.close()


# ================================================================
# ROTA: POST /api/status
# Salva ou atualiza o status de uma usina
# Chamada quando o vendedor clica em "Salvar status"
# ================================================================
@rotas.route("/api/status", methods=["POST"])
def salvar_status():
    """
    Recebe os dados do frontend e salva no banco.
    Usa INSERT OR UPDATE (upsert) — insere se não existir, atualiza se existir.
    """
    try:
        # Pega os dados enviados pelo frontend (JSON)
        dados = request.get_json()
        # request.get_json() = lê o corpo da requisição como JSON

        # Valida se os campos obrigatórios foram enviados
        if not dados or not dados.get("chave") or not dados.get("status"):
            return jsonify({"erro": "Campos obrigatórios: chave, status"}), 400
            # 400 = Bad Request (requisição inválida)

        # Extrai os campos do JSON recebido
        chave      = dados["chave"]
        status     = dados["status"]
        vendedor   = dados.get("vendedor", "")    # .get com padrão "" se não enviar
        observacao = dados.get("observacao", "")

        # Valida se o status é um valor permitido
        status_permitidos = ["novo", "contatado", "proposta", "descartado"]
        if status not in status_permitidos:
            return jsonify({"erro": f"Status inválido. Use: {status_permitidos}"}), 400

        conn = obter_conexao()
        cursor = conn.cursor()

        # INSERT INTO ... ON DUPLICATE KEY UPDATE
        # Se a chave já existir no banco → atualiza (UPDATE)
        # Se a chave não existir → insere (INSERT)
        # Isso evita duplicatas sem precisar verificar antes
        cursor.execute("""
            INSERT INTO status_usinas (chave, status, vendedor, observacao)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                status     = VALUES(status),
                vendedor   = VALUES(vendedor),
                observacao = VALUES(observacao),
                atualizado_em = CURRENT_TIMESTAMP
        """, (chave, status, vendedor, observacao))
        # %s = placeholder seguro contra SQL injection
        # Os valores são passados separadamente como tupla

        conn.commit()  # Confirma a operação no banco

        return jsonify({
            "mensagem": "Status salvo com sucesso!",
            "chave": chave,
            "status": status
        }), 200

    except Exception as e:
        print(f"❌ Erro ao salvar status: {e}")
        return jsonify({"erro": str(e)}), 500

    finally:
        if cursor: cursor.close()
        if conn: conn.close()


# ================================================================
# ROTA: GET /api/status/<chave>
# Retorna o status de UMA usina específica
# Útil para verificar o status mais recente antes de mostrar
# ================================================================
@rotas.route("/api/status/<path:chave>", methods=["GET"])
def buscar_status_usina(chave):
    """
    Busca o status de uma usina específica pela chave lat,lng.
    <path:chave> = aceita barras e vírgulas na URL
    """
    try:
        conn = obter_conexao()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT status, vendedor, observacao,
                   DATE_FORMAT(atualizado_em, '%d/%m/%Y %H:%i') as atualizado_em
            FROM status_usinas
            WHERE chave = %s
        """, (chave,))
        # A vírgula depois de chave é obrigatória para criar uma tupla de 1 elemento
        # sem ela Python trata como string, não como tupla

        linha = cursor.fetchone()
        # fetchone = busca apenas o primeiro resultado

        if linha:
            return jsonify(linha), 200
        else:
            # Se não encontrar, retorna status padrão "novo"
            return jsonify({
                "status": "novo",
                "vendedor": "",
                "observacao": "",
                "atualizado_em": ""
            }), 200

    except Exception as e:
        return jsonify({"erro": str(e)}), 500

    finally:
        if cursor: cursor.close()
        if conn: conn.close()


# ================================================================
# ROTA: GET /api/resumo
# Retorna estatísticas gerais para o dashboard
# ================================================================
@rotas.route("/api/resumo", methods=["GET"])
def resumo():
    """Retorna contagem de usinas por status para o dashboard"""
    try:
        conn = obter_conexao()
        cursor = conn.cursor(dictionary=True)

        # Conta quantas usinas existem por status
        cursor.execute("""
            SELECT status, COUNT(*) as total
            FROM status_usinas
            GROUP BY status
        """)
        # GROUP BY = agrupa os resultados por status e conta cada grupo

        linhas = cursor.fetchall()

        # Monta o resultado com zeros para status sem registros
        resultado = {
            "novo":       0,
            "contatado":  0,
            "proposta":   0,
            "descartado": 0
        }

        for linha in linhas:
            resultado[linha["status"]] = linha["total"]

        return jsonify(resultado), 200

    except Exception as e:
        return jsonify({"erro": str(e)}), 500

    finally:
        if cursor: cursor.close()
        if conn: conn.close()