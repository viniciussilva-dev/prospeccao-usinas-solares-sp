// ================================================================
// DADOS.JS — Carrega e processa os dois arquivos CSV
// Este arquivo é o primeiro a rodar — todos os outros dependem dele
// ================================================================


// ================================================================
// VARIÁVEL GLOBAL — armazena todas as usinas depois de carregar
// "let" cria uma variável que pode ser alterada depois
// Começa vazia [] e será preenchida com os dados dos CSVs
// ================================================================
let todasUsinas = [];        // Array com todas as 779 usinas combinadas
let statusUsinas = {};       // Objeto para guardar status vindos do backend
                             // Formato: { "lat,lng": { status, vendedor, observacao } }


// ================================================================
// VARIÁVEL DA URL DO BACKEND
// Aponta para onde o servidor Flask está rodando
// Em desenvolvimento: localhost (sua máquina)
// Em produção: troca pela URL do Railway/Render
// ================================================================
const URL_BACKEND = "http://localhost:5001";


// ================================================================
// FUNÇÃO PRINCIPAL — carrega os dois CSVs em paralelo
// É chamada automaticamente quando a página abre (última linha)
// ================================================================
function carregarDados() {

    console.log("📂 Iniciando carregamento dos CSVs...");
    // console.log mostra mensagens no console do navegador (F12)

    // Promise.all = executa as duas leituras AO MESMO TEMPO
    // mais rápido do que ler um CSV, esperar terminar, ler o outro
    Promise.all([
        lerCSV("dados/lista_vendas.csv"),       // CSV com nome, telefone, endereço
        lerCSV("dados/lista_vendas_solar.csv"), // CSV com dados solares
        buscarStatusBackend()                   // Busca status salvo no banco
    ])
    .then(function(resultados) {
        // .then = executa quando TUDO terminar de carregar
        // resultados[0] = dados do lista_vendas.csv
        // resultados[1] = dados do lista_vendas_solar.csv
        // resultados[2] = status do backend (pode ser vazio se backend offline)

        const dadosMaps  = resultados[0];   // Array de objetos do CSV Maps
        const dadosSolar = resultados[1];   // Array de objetos do CSV Solar
        const statusBanco = resultados[2];  // Objeto com status do banco

        console.log(`✅ Maps: ${dadosMaps.length} registros`);
        console.log(`✅ Solar: ${dadosSolar.length} registros`);
        console.log(`✅ Status do banco: ${Object.keys(statusBanco).length} registros`);

        // Salva o status do banco na variável global
        statusUsinas = statusBanco;

        // Cruza os dois CSVs usando latitude+longitude como chave
        todasUsinas = cruzarDados(dadosMaps, dadosSolar);

        console.log(`✅ Total após cruzamento: ${todasUsinas.length} usinas`);

        // Avisa os outros arquivos JS que os dados estão prontos
        // Cada função está definida em seu respectivo arquivo
        atualizarCards();   // Atualiza os 4 números no topo (dados.js)
        iniciarTabela();    // Monta a tabela (tabela.js)
        // O mapa é iniciado pelo Google Maps via callback=iniciarMapa (mapa.js)
    })
    .catch(function(erro) {
        // .catch = executa se qualquer leitura falhar
        console.error("❌ Erro ao carregar dados:", erro);
        alert("Erro ao carregar os dados. Verifique se os arquivos CSV estão na pasta 'dados/'");
    });
}


// ================================================================
// FUNÇÃO: LER UM ARQUIVO CSV
// Usa a biblioteca PapaParse para ler e converter em array de objetos
// Retorna uma Promise (promessa de que vai retornar os dados)
// ================================================================
function lerCSV(caminho) {

    // Promise = objeto que representa uma operação assíncrona (que demora)
    return new Promise(function(resolve, reject) {

        Papa.parse(caminho, {
            // download: true = busca o arquivo pelo caminho
            download: true,

            // header: true = usa a primeira linha do CSV como nomes das colunas
            // sem isso, as colunas seriam acessadas por índice (0, 1, 2...)
            header: true,

            // skipEmptyLines = ignora linhas em branco no CSV
            skipEmptyLines: true,

            // delimiter = separador das colunas (nosso CSV usa ponto e vírgula)
            delimiter: ";",

            // complete = função chamada quando terminar de ler
            complete: function(resultado) {
                resolve(resultado.data); // Retorna o array de objetos
            },

            // error = função chamada se der erro
            error: function(erro) {
                reject(erro);
            }
        });
    });
}


// ================================================================
// FUNÇÃO: BUSCAR STATUS DO BACKEND
// Tenta buscar os status salvos no banco MySQL
// Se o backend estiver offline, retorna objeto vazio (não quebra)
// ================================================================
function buscarStatusBackend() {
    return fetch(`${URL_BACKEND}/api/status`)
        .then(function(resposta) {
            // resposta.ok = true se o servidor respondeu com sucesso (200)
            if (resposta.ok) {
                return resposta.json(); // Converte o JSON recebido em objeto JS
            }
            // Se o servidor respondeu com erro, retorna objeto vazio
            return {};
        })
        .catch(function() {
            // Se o backend estiver offline, não quebra a página
            // Apenas avisa no console e continua sem status
            console.warn("⚠️ Backend offline — status não carregado");
            return {};
        });
}


// ================================================================
// FUNÇÃO: CRUZAR OS DOIS CSVs
// Une os dados do lista_vendas com os dados do lista_vendas_solar
// Usa latitude+longitude como chave de cruzamento (igual ao cache)
// ================================================================
function cruzarDados(dadosMaps, dadosSolar) {

    // Cria um "mapa" (dicionário) do CSV solar indexado por "lat,lng"
    // Isso permite buscar dados solares rapidamente pelo par de coordenadas
    const indexSolar = {};

    dadosSolar.forEach(function(linha) {
        // Pega a latitude e longitude de cada linha do CSV solar
        const lat = (linha["Latitude"] || "").toString().trim();
        const lng = (linha["Longitude"] || "").toString().trim();

        if (lat && lng) {
            // Cria a chave "lat,lng" e salva os dados solares nela
            const chave = `${lat},${lng}`;
            indexSolar[chave] = linha;
        }
    });

    // Agora percorre o CSV Maps e adiciona os dados solares em cada usina
    return dadosMaps.map(function(usina) {

        const lat = (usina["Latitude"] || "").toString().trim();
        const lng = (usina["Longitude"] || "").toString().trim();
        const chave = `${lat},${lng}`;

        // Busca os dados solares correspondentes (pode ser null se não encontrar)
        const solar = indexSolar[chave] || null;

        // Busca o status do banco MySQL (pode ser null se não tiver status)
        const statusBanco = statusUsinas[chave] || null;

        // Converte potência para número (vem como texto no CSV)
        const potencia = parseFloat(
            (usina["Potência (kW)"] || "0").toString().replace(",", ".")
        ) || 0;

        // Converte potencial de expansão para número (pode estar vazio)
        const expansao = solar
            ? parseFloat((solar["Potencial Expansão kW"] || "0").toString().replace(",", ".")) || 0
            : 0;

        // Retorna um objeto combinado com todos os dados da usina
        return {
            // === Dados de identificação ===
            chave: chave,           // "lat,lng" — identificador único

            // === Dados da ANEEL (CSV Maps) ===
            titular:   usina["Titular ANEEL"] || "",
            municipio: usina["Município"] || "",
            potencia:  potencia,

            // === Dados do Google Maps (CSV Maps) ===
            nomeNaMaps: usina["Nome no Maps"] || "",
            telefone:   usina["Telefone"] || "",
            endereco:   usina["Endereço"] || "",
            site:       usina["Site"] || "",

            // === Coordenadas ===
            lat: parseFloat(lat) || 0,  // Converte string para número decimal
            lng: parseFloat(lng) || 0,

            // === Dados da Solar API (CSV Solar — pode ser null) ===
            temSolar:   solar !== null,
            areaTelhado: solar ? parseFloat((solar["Área Telhado m²"] || "0").replace(",", ".")) || 0 : 0,
            maxPaineis:  solar ? parseInt(solar["Máx Painéis"] || "0") || 0 : 0,
            horasSol:    solar ? parseFloat((solar["Horas Sol/Ano"] || "0").replace(",", ".")) || 0 : 0,
            expansao:    expansao,
            economiaUSD: solar ? parseFloat((solar["Economia Anual USD"] || "0").replace(",", ".")) || 0 : 0,

            // === Status do vendedor (do banco MySQL) ===
            // Se não tiver status no banco, começa como "novo"
            status:      statusBanco ? statusBanco.status : "novo",
            vendedor:    statusBanco ? statusBanco.vendedor : "",
            observacao:  statusBanco ? statusBanco.observacao : "",
        };
    })
    .filter(function(usina) {
    // Remove coordenadas zeradas
    if (usina.lat === 0 || usina.lng === 0) return false;

    // === Filtra coordenadas dentro do estado de São Paulo ===
    // SP fica aproximadamente entre:
    // Latitude:  -25.3 (sul) até -19.7 (norte)
    // Longitude: -53.1 (oeste) até -44.1 (leste)
    const latValida = usina.lat >= -25.3 && usina.lat <= -19.7;
    const lngValida = usina.lng >= -53.1 && usina.lng <= -44.1;

    return latValida && lngValida;
});
}


// ================================================================
// FUNÇÃO: ATUALIZAR OS 4 CARDS DE RESUMO NO TOPO
// Calcula os números e insere no HTML
// ================================================================
function atualizarCards() {

    const total = todasUsinas.length;

    // Calcula a média de potência de todas as usinas
    const somaPotencia = todasUsinas.reduce(function(soma, u) {
        return soma + u.potencia;
        // reduce = percorre o array acumulando um valor
    }, 0); // 0 = valor inicial da soma
    const mediaPotencia = total > 0 ? Math.round(somaPotencia / total) : 0;

    // Conta quantas têm potencial de expansão maior que zero
    const comExpansao = todasUsinas.filter(function(u) {
        return u.expansao > 0;
    }).length;

    // Encontra o maior potencial de expansão
    const maiorExpansao = todasUsinas.reduce(function(maior, u) {
        return u.expansao > maior ? u.expansao : maior;
    }, 0);

    // Insere os valores no HTML — getElementById busca o elemento pelo id
    document.getElementById("num-total").textContent =
        total.toLocaleString("pt-BR");
        // toLocaleString formata o número com ponto separador de milhar (1.191)

    document.getElementById("num-potencia").textContent =
        mediaPotencia.toLocaleString("pt-BR");

    document.getElementById("num-expansao").textContent =
        comExpansao.toLocaleString("pt-BR");

    document.getElementById("num-maior").textContent =
        maiorExpansao.toLocaleString("pt-BR", { maximumFractionDigits: 0 });
}


// ================================================================
// FUNÇÃO: SALVAR STATUS NO BACKEND
// Chamada pelo botão "Salvar status" no painel lateral
// Envia os dados para o Flask que salva no MySQL
// ================================================================
function salvarStatusNoBanco(chave, status, vendedor, observacao) {

    // fetch = faz uma requisição HTTP para o backend
    return fetch(`${URL_BACKEND}/api/status`, {
        method: "POST",     // POST = envia dados (diferente de GET que só busca)
        headers: {
            // Avisa o servidor que estamos enviando JSON
            "Content-Type": "application/json"
        },
        // JSON.stringify converte o objeto JS para texto JSON
        body: JSON.stringify({
            chave:      chave,
            status:     status,
            vendedor:   vendedor,
            observacao: observacao
        })
    })
    .then(function(resposta) {
        if (resposta.ok) {
            console.log("✅ Status salvo no banco!");

            // Atualiza a variável local para refletir imediatamente
            statusUsinas[chave] = { status, vendedor, observacao };

            // Atualiza o status na usina correspondente
            const usina = todasUsinas.find(u => u.chave === chave);
            if (usina) {
                usina.status     = status;
                usina.vendedor   = vendedor;
                usina.observacao = observacao;
            }

            return true;
        }
        throw new Error("Erro ao salvar");
    })
    .catch(function(erro) {
        console.error("❌ Erro ao salvar status:", erro);
        alert("Erro ao salvar. Verifique se o backend está rodando.");
        return false;
    });
}


// ================================================================
// INICIA O CARREGAMENTO QUANDO A PÁGINA ABRE
// DOMContentLoaded = evento que dispara quando o HTML foi lido completamente
// Garante que todos os elementos existem antes de manipulá-los
// ================================================================
document.addEventListener("DOMContentLoaded", function() {
    carregarDados();
});