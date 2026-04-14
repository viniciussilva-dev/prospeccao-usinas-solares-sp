// ================================================================
// TABELA.JS — Controla a tabela filtrável e ordenável
// Depende de dados.js — precisa que todasUsinas esteja preenchido
// ================================================================


// ================================================================
// VARIÁVEIS DE CONTROLE DA TABELA
// ================================================================
let usinasFiltradas = [];   // Array com as usinas após aplicar os filtros
let colunaOrdem = -1;       // Qual coluna está sendo ordenada (-1 = nenhuma)
let ordemAsc = true;        // true = crescente (A-Z), false = decrescente (Z-A)


// ================================================================
// FUNÇÃO: INICIAR A TABELA
// Chamada por dados.js quando os CSVs terminam de carregar
// ================================================================
function iniciarTabela() {
    console.log("📊 Iniciando tabela...");
    usinasFiltradas = [...todasUsinas];
    renderizarTabela();
}


// ================================================================
// FUNÇÃO: RENDERIZAR A TABELA
// ================================================================
function renderizarTabela() {

    const tbody = document.getElementById("tabela-corpo");

    document.getElementById("tabela-contador").textContent =
        `${usinasFiltradas.length} usinas`;

    if (usinasFiltradas.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="8" style="text-align:center; padding:40px; color:#64748b;">
                    <i class="fa-solid fa-magnifying-glass" style="margin-right:8px;"></i>
                    Nenhuma usina encontrada com esses filtros
                </td>
            </tr>
        `;
        return;
    }

    const html = usinasFiltradas.map(function(usina) {

        const corStatus = {
            novo:       "#22c55e",
            contatado:  "#3b82f6",
            proposta:   "#f97316",
            descartado: "#ef4444"
        }[usina.status] || "#22c55e";

        const textoStatus = {
            novo:       "Não contatado",
            contatado:  "Contatado",
            proposta:   "Proposta enviada",
            descartado: "Descartado"
        }[usina.status] || "Não contatado";

        const titular    = truncar(usina.titular, 35);
        const nomeNaMaps = truncar(usina.nomeNaMaps, 25);

        const expansaoHtml = usina.expansao > 0
            ? `<span class="td-expansao">+${usina.expansao.toLocaleString("pt-BR")}</span>`
            : usina.temSolar
                ? `<span style="color:#94a3b8">0</span>`
                : `<span style="color:#cbd5e1">—</span>`;

        const areaHtml = usina.areaTelhado > 0
            ? usina.areaTelhado.toLocaleString("pt-BR", { maximumFractionDigits: 0 })
            : `<span style="color:#cbd5e1">—</span>`;

        const telefoneHtml = usina.telefone
            ? `<a href="tel:${usina.telefone}" style="color:#3b82f6; text-decoration:none;">${usina.telefone}</a>`
            : `<span style="color:#cbd5e1">—</span>`;

        return `
            <tr
                id="linha-${usina.chave.replace(/[^a-zA-Z0-9]/g, '_')}"
                onclick="selecionarUsinaTabela('${usina.chave}')"
                title="Clique para ver no mapa"
            >
                <td class="td-titular" title="${usina.titular}">${titular}</td>
                <td>${usina.municipio}</td>
                <td class="td-numero">${usina.potencia.toLocaleString("pt-BR")}</td>
                <td title="${usina.nomeNaMaps}">${nomeNaMaps || "—"}</td>
                <td>${telefoneHtml}</td>
                <td class="td-numero">${expansaoHtml}</td>
                <td class="td-numero">${areaHtml}</td>
                <td>
                    <span style="display:flex; align-items:center; gap:6px;">
                        <span style="
                            width:8px; height:8px; border-radius:50%;
                            background:${corStatus}; flex-shrink:0;
                        "></span>
                        ${textoStatus}
                    </span>
                </td>
            </tr>
        `;
    }).join("");

    tbody.innerHTML = html;
}


// ================================================================
// FUNÇÃO: FILTRAR A TABELA
// ================================================================
function filtrarTabela() {

    const textoBusca = document.getElementById("filtro-busca").value
        .toLowerCase()
        .trim();

    const potenciaMin = parseFloat(
        document.getElementById("filtro-potencia").value
    ) || 0;

    const tipoFiltro = document.getElementById("filtro-tipo").value;

    usinasFiltradas = todasUsinas.filter(function(usina) {

        if (textoBusca) {
            const titular   = (usina.titular || "").toLowerCase();
            const municipio = (usina.municipio || "").toLowerCase();
            const nome      = (usina.nomeNaMaps || "").toLowerCase();

            if (!titular.includes(textoBusca) &&
                !municipio.includes(textoBusca) &&
                !nome.includes(textoBusca)) {
                return false;
            }
        }

        if (potenciaMin > 0 && usina.potencia < potenciaMin) return false;

        if (tipoFiltro === "com_solar"    && !usina.temSolar) return false;
        if (tipoFiltro === "com_expansao" && usina.expansao <= 0) return false;
        if (tipoFiltro === "com_telefone" && !usina.telefone) return false;
        if (tipoFiltro === "novo"         && usina.status !== "novo") return false;
        if (tipoFiltro === "contatado"    && usina.status !== "contatado") return false;
        if (tipoFiltro === "proposta"     && usina.status !== "proposta") return false;
        if (tipoFiltro === "descartado"   && usina.status !== "descartado") return false;

        return true;
    });

    if (colunaOrdem >= 0) {
        aplicarOrdenacao();
    }

    renderizarTabela();
}


// ================================================================
// FUNÇÃO: ORDENAR A TABELA POR COLUNA
// ================================================================
function ordenarTabela(indiceColuna) {

    if (colunaOrdem === indiceColuna) {
        ordemAsc = !ordemAsc;
    } else {
        colunaOrdem = indiceColuna;
        ordemAsc = true;
    }

    aplicarOrdenacao();
    renderizarTabela();
}


// ================================================================
// FUNÇÃO: APLICAR A ORDENAÇÃO
// ================================================================
function aplicarOrdenacao() {

    usinasFiltradas.sort(function(a, b) {

        let valA, valB;

        switch (colunaOrdem) {
            case 0: valA = a.titular;     valB = b.titular;     break;
            case 1: valA = a.municipio;   valB = b.municipio;   break;
            case 2: valA = a.potencia;    valB = b.potencia;    break;
            case 5: valA = a.expansao;    valB = b.expansao;    break;
            case 6: valA = a.areaTelhado; valB = b.areaTelhado; break;
            default: return 0;
        }

        if (typeof valA === "string") valA = valA.toLowerCase();
        if (typeof valB === "string") valB = valB.toLowerCase();

        if (valA < valB) return ordemAsc ? -1 : 1;
        if (valA > valB) return ordemAsc ? 1 : -1;
        return 0;
    });
}


// ================================================================
// FUNÇÃO: LIMPAR TODOS OS FILTROS
// ================================================================
function limparFiltros() {
    document.getElementById("filtro-busca").value = "";
    document.getElementById("filtro-potencia").value = "";
    document.getElementById("filtro-tipo").value = "todos";

    colunaOrdem = -1;
    ordemAsc = true;

    usinasFiltradas = [...todasUsinas];
    renderizarTabela();
}


// ================================================================
// FUNÇÃO: SELECIONAR USINA PELA TABELA
//
// Chamada quando o usuário CLICA em uma linha da tabela.
// Comportamento:
//   1. Abre o painel lateral com os dados da usina
//   2. Sobe a página até o mapa (scroll para o topo)
//   3. Destaca a linha na tabela (amarelo)
// ================================================================
function selecionarUsinaTabela(chave) {

    const usina = todasUsinas.find(function(u) {
        return u.chave === chave;
    });
    if (!usina) return;

    const marcador = marcadores.find(function(m) {
        return m.usinaData && m.usinaData.chave === chave;
    });

    if (marcador) {
        // Abre o painel — o TRUE avisa que deve subir para o topo
        abrirPainel(usina, marcador, true);

        // Destaca a linha na tabela COM scroll (usuário clicou na tabela)
        destacarLinhaNaTabela(chave, false);
    }
}


// ================================================================
// FUNÇÃO: DESTACAR LINHA NA TABELA
//
// Parâmetro fazerScroll:
//   true  = clicou na tabela → destaca E faz scroll até a linha
//   false = clicou no mapa   → só destaca, SEM scroll
// ================================================================
function destacarLinhaNaTabela(chave, fazerScroll) {

    // Remove destaque de todas as linhas anteriores
    document.querySelectorAll(".linha-ativa").forEach(function(linha) {
        linha.classList.remove("linha-ativa");
    });

    // Garante que a usina está visível — se estiver filtrada, limpa os filtros
    const usinaExisteNaTabela = usinasFiltradas.find(function(u) {
        return u.chave === chave;
    });

    if (!usinaExisteNaTabela) {
        limparFiltros();
    }

    // Aguarda o DOM atualizar antes de destacar a linha
    setTimeout(function() {
        const id = "linha-" + chave.replace(/[^a-zA-Z0-9]/g, '_');
        const linha = document.getElementById(id);

        if (linha) {
            // Adiciona destaque amarelo
            linha.classList.add("linha-ativa");

            // Só faz scroll até a linha se for pedido (clique na tabela)
            // Quando vem do mapa (fazerScroll = false), não mexe no scroll
            if (fazerScroll) {
                linha.scrollIntoView({
                    behavior: "smooth",
                    block: "center"
                });
            }
        }
    }, 150);
}


// ================================================================
// FUNÇÃO AUXILIAR: TRUNCAR TEXTO LONGO
// ================================================================
function truncar(texto, limite) {
    if (!texto) return "—";
    if (texto.length <= limite) return texto;
    return texto.substring(0, limite) + "...";
}