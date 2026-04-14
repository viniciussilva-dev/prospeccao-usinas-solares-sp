// ================================================================
// MAPA.JS — Controla o mapa Google Maps e os marcadores (pins)
// Depende de dados.js — precisa que todasUsinas esteja preenchido
// ================================================================


// ================================================================
// VARIÁVEIS GLOBAIS DO MAPA
// ================================================================
let mapa;               // Objeto do mapa Google Maps
let marcadores = [];    // Array com todos os marcadores no mapa
let marcadorAtivo = null;   // Marcador atualmente selecionado
let usinaAtiva = null;      // Dados da usina atualmente selecionada
let statusSelecionado = null; // Status escolhido pelo vendedor no painel


// ================================================================
// CORES DOS PINS POR STATUS
// Cada status tem uma cor diferente no mapa
// ================================================================
const COR_STATUS = {
    novo:       "#22c55e",  // Verde — não contatado ainda
    contatado:  "#3b82f6",  // Azul — já entrou em contato
    proposta:   "#f97316",  // Laranja — proposta enviada
    descartado: "#ef4444",  // Vermelho — sem interesse
    semCoordenada: "#94a3b8" // Cinza — não encontrado no Maps
};


// ================================================================
// FUNÇÃO: INICIAR O MAPA
// Esta função é chamada automaticamente pelo Google Maps
// quando a API termina de carregar (callback=iniciarMapa no HTML)
// ================================================================
function iniciarMapa() {
    console.log("🗺️ Iniciando Google Maps...");

    // Cria o mapa dentro do elemento com id="mapa"
    mapa = new google.maps.Map(document.getElementById("mapa"), {

        // Centro inicial do mapa — coordenada central de São Paulo
        center: { lat: -22.5, lng: -48.5 },

        // Nível de zoom inicial (1=mundo inteiro, 20=rua)
        // 7 mostra o estado de SP inteiro
        zoom: 7,

        // Estilo do mapa — "roadmap" é o padrão com ruas
        mapTypeId: "roadmap",

        // Desativa controles desnecessários para deixar mais limpo
        fullscreenControl: false,
        mapTypeControl: false,
        streetViewControl: false,

        // Estilo visual minimalista
        styles: [
            {
                featureType: "poi",
                elementType: "labels",
                stylers: [{ visibility: "off" }]
            },
            {
                featureType: "transit",
                elementType: "labels",
                stylers: [{ visibility: "off" }]
            }
        ]
    });

    // Aguarda os dados dos CSVs estarem prontos antes de colocar os pins
    const intervalo = setInterval(function() {
        if (todasUsinas.length > 0) {
            clearInterval(intervalo);
            adicionarMarcadores();
        }
    }, 100);
}


// ================================================================
// FUNÇÃO: CRIAR UM ÍCONE DE PIN COLORIDO
// ================================================================
function criarIcone(cor) {
    const svg = `
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">
            <circle cx="12" cy="12" r="11" fill="white" stroke="${cor}" stroke-width="2"/>
            <circle cx="12" cy="12" r="7" fill="${cor}"/>
        </svg>
    `;

    return {
        url: "data:image/svg+xml;charset=UTF-8," + encodeURIComponent(svg),
        scaledSize: new google.maps.Size(24, 24),
        anchor: new google.maps.Point(12, 12)
    };
}


// ================================================================
// FUNÇÃO: ADICIONAR TODOS OS MARCADORES NO MAPA
// ================================================================
function adicionarMarcadores() {
    console.log(`📍 Adicionando ${todasUsinas.length} marcadores...`);

    marcadores.forEach(function(m) { m.setMap(null); });
    marcadores = [];

    todasUsinas.forEach(function(usina) {

        if (!usina.lat || !usina.lng) return;

        const cor = COR_STATUS[usina.status] || COR_STATUS.novo;

        const marcador = new google.maps.Marker({
            position: { lat: usina.lat, lng: usina.lng },
            map: mapa,
            icon: criarIcone(cor),
            title: usina.titular,
            optimized: true
        });

        marcador.usinaData = usina;

        // === Clique no mapa: abre painel SEM scroll ===
        marcador.addListener("click", function() {
            abrirPainel(usina, marcador, false);
        });

        marcadores.push(marcador);
    });

    console.log(`✅ ${marcadores.length} marcadores adicionados`);
}


// ================================================================
// FUNÇÃO: ABRIR O PAINEL LATERAL COM DETALHES DA USINA
//
// O parâmetro "fazerScrollTopo" controla o comportamento:
//   false = chamado pelo clique no mapa (não faz scroll)
//   true  = chamado pelo clique na tabela (faz scroll para o topo)
// ================================================================
function abrirPainel(usina, marcador, fazerScrollTopo) {

    // Padrão: não faz scroll (clique no mapa)
    if (fazerScrollTopo === undefined) fazerScrollTopo = false;

    usinaAtiva = usina;
    marcadorAtivo = marcador;
    statusSelecionado = usina.status;

    // Esconde painel vazio e mostra detalhes
    document.getElementById("painel-vazio").style.display = "none";
    document.getElementById("painel-detalhes").style.display = "flex";

    // Nome: usa nome do Maps se tiver, senão usa o titular da ANEEL
    const nome = usina.nomeNaMaps && usina.nomeNaMaps !== "Não encontrado"
        ? usina.nomeNaMaps
        : usina.titular;
    document.getElementById("detalhe-nome").textContent = nome;

    // Badge de status
    atualizarBadge(usina.status);

    // Dados da ANEEL
    document.getElementById("detalhe-titular").textContent = usina.titular || "—";
    document.getElementById("detalhe-municipio").textContent = usina.municipio || "—";
    document.getElementById("detalhe-potencia").textContent =
        usina.potencia ? `${usina.potencia.toLocaleString("pt-BR")} kW` : "—";

    // Dados do Google Maps
    document.getElementById("detalhe-telefone").textContent = usina.telefone || "—";
    document.getElementById("detalhe-endereco").textContent = usina.endereco || "—";

    const elSite = document.getElementById("detalhe-site");
    if (usina.site) {
        elSite.innerHTML = `<a href="${usina.site}" target="_blank" rel="noopener">${usina.site}</a>`;
    } else {
        elSite.textContent = "—";
    }

    // Dados Solares
    const secaoSolar = document.getElementById("secao-solar");
    if (usina.temSolar && usina.expansao >= 0) {
        secaoSolar.style.display = "block";

        document.getElementById("detalhe-area").textContent =
            usina.areaTelhado ? `${usina.areaTelhado.toLocaleString("pt-BR")} m²` : "—";

        document.getElementById("detalhe-paineis").textContent =
            usina.maxPaineis ? usina.maxPaineis.toLocaleString("pt-BR") : "—";

        document.getElementById("detalhe-horas-sol").textContent =
            usina.horasSol ? `${usina.horasSol.toLocaleString("pt-BR")} h/ano` : "—";

        document.getElementById("detalhe-expansao").textContent =
            usina.expansao > 0
                ? `+${usina.expansao.toLocaleString("pt-BR")} kW`
                : "Telhado no limite";

        document.getElementById("detalhe-economia").textContent =
            usina.economiaUSD
                ? `US$ ${usina.economiaUSD.toLocaleString("pt-BR")}/ano`
                : "—";
    } else {
        secaoSolar.style.display = "none";
    }

    // Campos do vendedor
    document.getElementById("input-observacao").value = usina.observacao || "";
    if (usina.vendedor) {
        document.getElementById("input-vendedor").value = usina.vendedor;
    }

    // Botões de status
    atualizarBotoesStatus(usina.status);

    // Destaca linha na tabela SEM fazer scroll (scroll é controlado fora)
    destacarLinhaNaTabela(usina.chave, false);

    // Centraliza o mapa na usina clicada
    mapa.panTo({ lat: usina.lat, lng: usina.lng });

    // === Se chamado pela tabela, sobe para o topo da página ===
    if (fazerScrollTopo) {
        window.scrollTo({ top: 0, behavior: "smooth" });
    }
}


// ================================================================
// FUNÇÃO: ATUALIZAR O BADGE DE STATUS NO PAINEL
// ================================================================
function atualizarBadge(status) {
    const badge = document.getElementById("detalhe-badge");

    const textos = {
        novo:       "Não contatado",
        contatado:  "Contatado",
        proposta:   "Proposta enviada",
        descartado: "Descartado"
    };

    badge.textContent = textos[status] || "Não contatado";
    badge.className = "badge";
    badge.classList.add(`badge-${status || "novo"}`);
}


// ================================================================
// FUNÇÃO: DESTACAR O BOTÃO DO STATUS ATUAL
// ================================================================
function atualizarBotoesStatus(statusAtual) {
    const botoes = document.querySelectorAll(".btn-status");

    botoes.forEach(function(botao) {
        botao.classList.remove("ativo");

        if (botao.classList.contains(statusAtual)) {
            botao.classList.add("ativo");
        }
    });
}


// ================================================================
// FUNÇÃO: SELECIONAR STATUS
// ================================================================
function selecionarStatus(status) {
    statusSelecionado = status;
    atualizarBotoesStatus(status);
    atualizarBadge(status);
}


// ================================================================
// FUNÇÃO: SALVAR STATUS
// ================================================================
function salvarStatus() {

    if (!usinaAtiva) {
        alert("Selecione uma usina no mapa primeiro.");
        return;
    }

    const status     = statusSelecionado || "novo";
    const vendedor   = document.getElementById("input-vendedor").value.trim();
    const observacao = document.getElementById("input-observacao").value.trim();

    if (!vendedor) {
        alert("Por favor, informe seu nome antes de salvar.");
        document.getElementById("input-vendedor").focus();
        return;
    }

    salvarStatusNoBanco(usinaAtiva.chave, status, vendedor, observacao)
        .then(function(sucesso) {
            if (sucesso) {
                const novaCor = COR_STATUS[status] || COR_STATUS.novo;
                marcadorAtivo.setIcon(criarIcone(novaCor));

                const btnSalvar = document.querySelector(".btn-salvar");
                const textoOriginal = btnSalvar.innerHTML;
                btnSalvar.innerHTML = '<i class="fa-solid fa-check"></i> Salvo!';
                btnSalvar.style.background = "#22c55e";

                setTimeout(function() {
                    btnSalvar.innerHTML = textoOriginal;
                    btnSalvar.style.background = "";
                }, 2000);

                renderizarTabela();
            }
        });
}


// ================================================================
// FUNÇÃO: ATUALIZAR COR DE UM MARCADOR ESPECÍFICO
// ================================================================
function atualizarCorMarcador(chave, status) {
    const marcador = marcadores.find(function(m) {
        return m.usinaData && m.usinaData.chave === chave;
    });

    if (marcador) {
        const cor = COR_STATUS[status] || COR_STATUS.novo;
        marcador.setIcon(criarIcone(cor));
    }
}