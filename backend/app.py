# ================================================================
# APP.PY — Servidor Flask principal
# Ponto de entrada do backend — rode este arquivo para iniciar
# ================================================================

# === IMPORTS ===
from flask import Flask         # Framework web para criar o servidor
from flask_cors import CORS     # Permite o frontend acessar o backend
                                # CORS = Cross-Origin Resource Sharing
                                # Necessário porque frontend e backend
                                # rodam em domínios/portas diferentes
from banco import inicializar_banco  # Nossa função de setup do banco
from rotas import rotas              # Nossas rotas da API


# ================================================================
# CRIA A APLICAÇÃO FLASK
# __name__ = nome do módulo atual (app.py)
# Flask usa isso para encontrar arquivos relativos
# ================================================================
app = Flask(__name__)


# ================================================================
# CONFIGURAÇÃO DO CORS
# Permite que o frontend (outro domínio) acesse o backend
# Sem isso o navegador bloquearia as requisições por segurança
# ================================================================
CORS(app, resources={
    r"/api/*": {
        # origins = quais domínios podem acessar a API
        # Em produção, troca "*" pelo domínio real do frontend
        # Ex: "https://seu-frontend.github.io"
        "origins": "*",

        # methods = quais métodos HTTP são permitidos
        "methods": ["GET", "POST", "OPTIONS"],

        # headers = quais cabeçalhos são permitidos
        "allow_headers": ["Content-Type"]
    }
})


# ================================================================
# REGISTRA AS ROTAS
# Conecta o arquivo rotas.py ao app Flask
# ================================================================
app.register_blueprint(rotas)


# ================================================================
# ROTA DE SAÚDE — verifica se o backend está funcionando
# Acesse http://localhost:5000/health para testar
# ================================================================
@app.route("/health")
def health():
    """Rota simples para verificar se o servidor está rodando"""
    return {"status": "ok", "mensagem": "Backend rodando!"}, 200


# ================================================================
# INICIALIZAÇÃO DO SERVIDOR
# Só executa quando rodamos diretamente: python app.py
# Não executa quando importado por outros módulos
# ================================================================
if __name__ == "__main__":

    print("🚀 Iniciando servidor Flask...")

    # Inicializa o banco de dados (cria tabelas se não existirem)
    inicializar_banco()

    # Inicia o servidor
    app.run(
        host="0.0.0.0",  # Aceita conexões de qualquer IP
                          # "0.0.0.0" = acessível na rede local
                          # "127.0.0.1" = só na própria máquina
        port=5001,        # Porta onde o servidor vai rodar
        debug=True        # debug=True = reinicia automaticamente ao salvar
                          # IMPORTANTE: desativar em produção (debug=False)
    )
    
    