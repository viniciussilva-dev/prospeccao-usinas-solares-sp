# ================================================================
# BANCO.PY — Configuração e conexão com o banco MySQL
# Responsável por criar a tabela e fornecer conexões
# ================================================================

# === IMPORTS ===
import mysql.connector   # Biblioteca para conectar ao MySQL
import os                # Para ler variáveis de ambiente do .env
from dotenv import load_dotenv  # Para carregar o arquivo .env

# Carrega as variáveis do arquivo .env
load_dotenv()


# ================================================================
# CONFIGURAÇÕES DO BANCO — lidas do arquivo .env
# Nunca coloque senhas direto no código!
# ================================================================
CONFIG_BANCO = {
    "host":     os.getenv("DB_HOST", "localhost"),  # Endereço do servidor MySQL
    "port":     int(os.getenv("DB_PORT", 3306)),    # Porta padrão do MySQL
    "user":     os.getenv("DB_USER", "root"),       # Usuário do banco
    "password": os.getenv("DB_PASSWORD", ""),       # Senha do banco
    "database": os.getenv("DB_NAME", "prospeccao_solar"), # Nome do banco
}


# ================================================================
# FUNÇÃO: OBTER CONEXÃO COM O BANCO
# Retorna uma conexão ativa para fazer operações
# Cada função que precisa do banco chama esta função
# ================================================================
def obter_conexao():
    """Cria e retorna uma conexão com o banco MySQL"""
    return mysql.connector.connect(**CONFIG_BANCO)
    # ** desempacota o dicionário como parâmetros nomeados


# ================================================================
# FUNÇÃO: CRIAR BANCO E TABELA SE NÃO EXISTIREM
# Chamada uma vez quando o servidor inicia
# ================================================================
def inicializar_banco():
    """
    Cria o banco de dados e a tabela de status se não existirem.
    IF NOT EXISTS = não dá erro se já existir
    """
    try:
        # Primeiro conecta sem especificar o banco (para poder criá-lo)
        conn = mysql.connector.connect(
            host=CONFIG_BANCO["host"],
            port=CONFIG_BANCO["port"],
            user=CONFIG_BANCO["user"],
            password=CONFIG_BANCO["password"]
        )
        cursor = conn.cursor()

        # Cria o banco de dados se não existir
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS {CONFIG_BANCO['database']} "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            # utf8mb4 = suporte completo a emojis e caracteres especiais
        )

        # Seleciona o banco criado
        cursor.execute(f"USE {CONFIG_BANCO['database']}")

        # Cria a tabela de status das usinas
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS status_usinas (
                id          INT AUTO_INCREMENT PRIMARY KEY,
                -- AUTO_INCREMENT = id gerado automaticamente (1, 2, 3...)

                chave       VARCHAR(50) UNIQUE NOT NULL,
                -- chave = "lat,lng" — identificador único da usina
                -- UNIQUE = não permite duplicatas
                -- NOT NULL = campo obrigatório

                status      ENUM('novo','contatado','proposta','descartado')
                            NOT NULL DEFAULT 'novo',
                -- ENUM = só aceita esses valores específicos
                -- DEFAULT 'novo' = valor padrão se não informar

                vendedor    VARCHAR(100),
                -- Nome do vendedor que atualizou o status

                observacao  TEXT,
                -- Anotações livres do vendedor

                atualizado_em DATETIME DEFAULT CURRENT_TIMESTAMP
                              ON UPDATE CURRENT_TIMESTAMP,
                -- CURRENT_TIMESTAMP = data/hora atual
                -- ON UPDATE = atualiza automaticamente quando o registro muda

                criado_em   DATETIME DEFAULT CURRENT_TIMESTAMP
                -- Data de criação — não muda depois
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        conn.commit()  # Confirma as operações no banco
        print("✅ Banco inicializado com sucesso!")

    except Exception as e:
        print(f"❌ Erro ao inicializar banco: {e}")
        raise  # Re-lança o erro para o Flask tratar

    finally:
        # finally = sempre executa, mesmo se der erro
        # Garante que a conexão seja fechada
        if cursor: cursor.close()
        if conn: conn.close()