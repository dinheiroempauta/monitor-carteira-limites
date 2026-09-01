"""Monta a página HTML do dashboard de performance (Chart.js via CDN —
publicada no GitHub Pages, que não tem as restrições de CSP dos Artifacts).

Aplica o design system compartilhado da "Dinheiro em Pauta"
(docs/assets/site.css, site.js, theme-init.js — copiados uma vez do
pacote de identidade visual, não regenerados por este módulo): tokens de
cor/tipografia, masthead com alternância de tema, cards de gráfico e
padrão de formulário. É reuso da identidade visual, não uma página do
blog em si — por isso o wordmark do masthead diz "Monitor de Carteira",
sem link de volta pro blog.

O formulário de registro de transação direto pelo navegador (via API do
GitHub, token fine-grained salvo no localStorage) foi DESATIVADO —
`SHOW_TRANSACTION_FORM = False` — depois que o registro de transações
passou a ser automático via leitura das notas de negociação por e-mail
(ver `specs/003-importacao-automatica-notas/`). O código continua aqui,
intacto, para o caso de a automação por e-mail falhar e o usuário
precisar de novo do registro manual pelo site; só não é mais renderizado
por padrão."""
from __future__ import annotations

import json

from monitor.allocation import AssetStatus
from monitor.performance import MonthlyReturn

MES_ABREV = {
    1: "jan",
    2: "fev",
    3: "mar",
    4: "abr",
    5: "mai",
    6: "jun",
    7: "jul",
    8: "ago",
    9: "set",
    10: "out",
    11: "nov",
    12: "dez",
}

REPO_OWNER = "dinheiroempauta"
REPO_NAME = "monitor-carteira-limites"
FILE_PATH = "config/transactions.csv"
BRANCH = "main"

SHOW_TRANSACTION_FORM = False

_TEMPLATE = r"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<script src="assets/theme-init.js"></script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="preload" as="style" href="https://fonts.googleapis.com/css2?family=Fraunces:ital,wght@0,400;0,500;0,600;0,700;1,500;1,600&family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fraunces:ital,wght@0,400;0,500;0,600;0,700;1,500;1,600&family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap" media="print" onload="this.media='all'">
<noscript><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fraunces:ital,wght@0,400;0,500;0,600;0,700;1,500;1,600&family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap"></noscript>
<link rel="stylesheet" href="assets/site.css">
<meta name="color-scheme" content="light dark">
<title>Performance da Carteira</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<style>
  /* Sem eyebrow/H1 (removidos), a página usa quase a largura inteira da
     tela — maxw bem mais folgado que o padrão do blog (1440px), só pra
     não esticar demais em monitores ultrawide. */
  :root {{ --maxw: 2200px; }}

  /* Tudo cabe numa tela só, sem scroll em nenhuma direção (a 100% de
     zoom): a página inteira é uma coluna flex com a altura exata da
     viewport, e a única área que "respira" de verdade — o corpo do
     dashboard — recebe o espaço que sobra (flex: 1) depois de masthead,
     subtítulo e rodapé, todos compactados ao essencial. min-height: 0 em
     cada nível do flex/grid é o que impede o conteúdo de estourar e
     forçar rolagem. Abaixo de 900px de largura isso deixa de fazer
     sentido (gráficos empilhados não cabem em altura nenhuma) — nesse
     ponto volta-se a rolar normalmente. */
  html, body {{ height: 100%; }}
  body {{ display: flex; flex-direction: column; min-height: 0; overflow: hidden; }}
  main {{
    max-width: var(--maxw); width: 100%; margin: 0 auto; box-sizing: border-box;
    padding: 18px 28px 64px; flex: 1 1 auto; display: flex; flex-direction: column; min-height: 0;
  }}
  .page-subheading {{ margin: 0 0 18px; font-size: 13.5px; }}

  /* Layout: coluna esquerda = "Alvo, banda e posição atual" (70% da
     altura) com os 4 KPIs em grade 2x2 logo abaixo (30%) — os dois
     dividem a altura da coluna, em vez do gráfico ocupar tudo ou os
     KPIs formarem uma faixa à parte. Coluna direita = os dois gráficos
     de linha, empilhados, cada um usando a largura inteira da coluna
     (são os que mais se beneficiam de serem compridos na horizontal:
     mais pontos de tempo visíveis por vez). */
  .dash-grid {{ flex: 1 1 auto; min-height: 0; display: flex; gap: 14px; }}
  .left-col {{ flex: 1 1 0; min-width: 0; display: flex; flex-direction: column; gap: 14px; }}
  .left-col .chart-card {{ flex: 1 1 auto; }}
  .kpi-row {{ flex: 0 0 auto; display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }}
  .kpi-tile {{ border: 1px solid var(--line-strong); background: var(--paper-raised); border-radius: 3px; padding: 8px 14px; display: flex; flex-direction: column; justify-content: center; overflow: hidden; }}
  .kpi-tile .kpi-label {{ font-family: var(--font-mono); font-size: 10.5px; letter-spacing: .08em; text-transform: uppercase; color: var(--muted); margin-bottom: 4px; white-space: nowrap; }}
  .kpi-tile .kpi-value {{ font-family: var(--font-mono); font-size: 1.2rem; font-variant-numeric: tabular-nums; white-space: nowrap; }}
  .kpi-tile .kpi-value.positive {{ color: var(--green); }}
  .kpi-tile .kpi-value.negative {{ color: var(--brick); }}

  .line-charts {{ flex: 1.6 1 0; min-width: 0; min-height: 0; display: flex; flex-direction: column; gap: 14px; }}
  .line-charts .chart-card {{ flex: 1 1 0; }}

  .chart-card {{ margin: 0; min-height: 0; display: flex; flex-direction: column; padding: 12px 16px 10px; }}
  .chart-head {{ flex: 0 0 auto; margin-bottom: 4px; }}
  .chart-title {{ font-size: 0.95rem; }}
  @media (max-width: 900px) {{
    html, body {{ height: auto; overflow: visible; }}
    main {{ display: block; padding: 24px; }}
    .dash-grid {{ display: block; }}
    .left-col {{ display: block; margin-bottom: 14px; }}
    .left-col .chart-card {{ margin-bottom: 14px; }}
    .line-charts {{ display: block; }}
    .chart-card {{ margin: 0 0 14px; }}
    .chart-card .chart-svg-wrap {{ height: 320px; flex: none; }}
  }}
  .chart-svg-wrap {{ position: relative; flex: 1 1 auto; min-height: 0; }}
  .chart-svg-wrap canvas {{ max-width: 100%; }}

  .masthead {{ flex: 0 0 auto; padding: 8px 24px !important; }}

  .field-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px,1fr)); gap: 14px 16px; align-items: end; margin-bottom: 8px; }}
  .field {{ display: flex; flex-direction: column; gap: 6px; }}
  .field label {{ font-family: var(--font-mono); font-size: 12px; color: var(--ink); font-weight: 600; }}
  .field select {{
    font-family: var(--font-body); background: var(--paper); color: var(--ink); border: 1px solid var(--line-strong);
    border-radius: 3px; padding: 11px 12px; min-height: 44px;
  }}
  .token-setup {{ margin-bottom: 18px; font-size: 14.5px; }}
  .token-setup p {{ margin: 0 0 10px; }}
  .token-row {{ display: flex; gap: 8px; }}
  .token-row input {{ flex: 1; }}
  #tx-status {{ min-height: 1.3em; margin-top: 14px; font-size: 14px; }}
  .token-change {{ font-size: 13px; color: var(--muted); margin-top: 14px; }}
</style>
</head>
<body>

<div class="masthead">
  <div class="masthead-inner">
    <span class="wordmark"><span>Monitor</span> de Carteira</span>
    <div class="masthead-actions">
      <button type="button" class="icon-btn theme-toggle" id="themeToggle" aria-label="Alternar entre tema claro e escuro">
        <svg class="icon-sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"/></svg>
        <svg class="icon-moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79Z"/></svg>
      </button>
    </div>
  </div>
</div>

<main>
  <p class="page-subheading">Atualizado em {generated_at} — patrimônio e performance acumulam desde a primeira transação da carteira.</p>

  <div class="dash-grid">
    <div class="left-col">
      {kpi_section}
      <div class="chart-card">
        <div class="chart-head"><div class="chart-title">Alvo, banda e posição atual</div></div>
        <div class="chart-svg-wrap"><canvas id="composicao"></canvas></div>
      </div>
    </div>

    <div class="line-charts">
      <div class="chart-card">
        <div class="chart-head"><div class="chart-title">Patrimônio ao longo do tempo</div></div>
        <div class="chart-svg-wrap"><canvas id="patrimonio"></canvas></div>
      </div>
      <div class="chart-card">
        <div class="chart-head"><div class="chart-title">Performance mensal: nominal vs. real (descontada a inflação do mês)</div></div>
        <div class="chart-svg-wrap"><canvas id="performance"></canvas></div>
      </div>
    </div>
  </div>

  {form_section}
</main>

<script src="assets/site.js"></script>
<script>
const dados = {dados_json};

function fmtPct(v) {{
  if (v === null || v === undefined || Number.isNaN(v)) return '—';
  return v.toLocaleString('pt-BR', {{ minimumFractionDigits: 1, maximumFractionDigits: 1 }}) + '%';
}}
function fmtBRL(v) {{
  return v.toLocaleString('pt-BR', {{ style: 'currency', currency: 'BRL', minimumFractionDigits: 2, maximumFractionDigits: 2 }});
}}

function cssVar(name) {{
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}}

let charts = [];

function corDoTema() {{
  return {{
    green: cssVar('--green'),
    gold: cssVar('--gold'),
    brick: cssVar('--brick'),
    muted: cssVar('--muted'),
    line: cssVar('--line'),
    ink: cssVar('--ink'),
  }};
}}

function montarGraficos() {{
  const cor = corDoTema();
  charts.forEach(c => c.destroy());
  charts = [];

  const statusCor = {{ ok: cor.green, abaixo_da_banda: cor.gold, acima_da_banda: cor.brick }};

  charts.push(new Chart(document.getElementById('composicao'), {{
    data: {{
      labels: dados.composicao.map(a => a.ticker),
      datasets: [
        {{
          type: 'bar',
          label: 'Banda',
          data: dados.composicao.map(a => [a.min, a.max]),
          backgroundColor: cor.line,
          borderRadius: 3,
          barPercentage: 0.5,
          order: 2,
        }},
        {{
          type: 'line',
          label: 'Alvo',
          data: dados.composicao.map(a => a.alvo),
          showLine: false,
          pointStyle: 'line',
          pointRadius: 16,
          pointBorderWidth: 3,
          pointBorderColor: cor.ink,
          order: 1,
        }},
        {{
          type: 'line',
          label: 'Atual',
          data: dados.composicao.map(a => a.pct),
          showLine: false,
          pointStyle: 'circle',
          pointRadius: 6,
          pointBackgroundColor: dados.composicao.map(a => statusCor[a.status]),
          pointBorderColor: dados.composicao.map(a => statusCor[a.status]),
          order: 0,
        }},
      ]
    }},
    options: {{
      responsive: true,
      maintainAspectRatio: false,
      interaction: {{ mode: 'index', intersect: false }},
      scales: {{
        x: {{ ticks: {{ color: cor.ink }}, grid: {{ display: false }} }},
        y: {{ ticks: {{ color: cor.muted, callback: v => fmtPct(v) }}, grid: {{ color: cor.line }} }}
      }},
      plugins: {{
        legend: {{ labels: {{ color: cor.ink }} }},
        tooltip: {{
          callbacks: {{
            label: c => c.dataset.label === 'Banda'
              ? `Banda: ${{fmtPct(c.raw[0])}} – ${{fmtPct(c.raw[1])}}`
              : `${{c.dataset.label}}: ${{fmtPct(c.raw)}}`
          }}
        }}
      }}
    }}
  }}));

  charts.push(new Chart(document.getElementById('patrimonio'), {{
    type: 'line',
    data: {{
      labels: dados.patrimonio.map(p => p.data),
      datasets: [{{ label: 'Patrimônio', data: dados.patrimonio.map(p => p.valor), borderColor: cor.green, backgroundColor: cor.green, tension: 0.15, pointHoverRadius: 5 }}]
    }},
    options: {{
      responsive: true,
      maintainAspectRatio: false,
      interaction: {{ mode: 'index', intersect: false }},
      scales: {{
        x: {{ ticks: {{ color: cor.muted }}, grid: {{ color: cor.line }} }},
        y: {{ ticks: {{ color: cor.muted, callback: v => fmtBRL(v) }}, grid: {{ color: cor.line }} }}
      }},
      plugins: {{
        legend: {{ labels: {{ color: cor.ink }} }},
        tooltip: {{ callbacks: {{ label: c => `${{c.dataset.label}}: ${{fmtBRL(c.raw)}}` }} }}
      }}
    }}
  }}));

  charts.push(new Chart(document.getElementById('performance'), {{
    type: 'bar',
    data: {{
      labels: dados.performance.map(p => p.mes),
      datasets: [
        {{ label: 'Nominal', data: dados.performance.map(p => p.nominal), backgroundColor: cor.green, borderRadius: 3 }},
        {{ label: 'Real (descontado IPCA do mês)', data: dados.performance.map(p => p.real), backgroundColor: cor.gold, borderRadius: 3 }}
      ]
    }},
    options: {{
      responsive: true,
      maintainAspectRatio: false,
      interaction: {{ mode: 'index', intersect: false }},
      scales: {{
        x: {{ ticks: {{ color: cor.ink }}, grid: {{ display: false }} }},
        y: {{ ticks: {{ color: cor.muted, callback: v => fmtPct(v) }}, grid: {{ color: cor.line }} }}
      }},
      plugins: {{
        legend: {{ labels: {{ color: cor.ink }} }},
        tooltip: {{
          callbacks: {{
            label: c => c.raw === null
              ? `${{c.dataset.label}}: sem dado ainda (IPCA do mês não publicado)`
              : `${{c.dataset.label}}: ${{fmtPct(c.raw)}}`
          }}
        }}
      }}
    }}
  }}));
}}

montarGraficos();

// Recolore os gráficos depois que o botão de tema (site.js) já trocou o
// data-theme — precisa vir DEPOIS do listener do site.js (registrado
// quando o <script src="assets/site.js"> rodou, antes deste bloco), já
// que dois listeners no mesmo evento disparam na ordem de registro.
const themeToggleBtn = document.getElementById('themeToggle');
if (themeToggleBtn) {{
  themeToggleBtn.addEventListener('click', () => setTimeout(montarGraficos, 0));
}}
if (window.matchMedia) {{
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {{
    if (!document.documentElement.getAttribute('data-theme')) montarGraficos();
  }});
}}

{form_script}
</script>
</body>
</html>
"""

# Bloco do formulário de registro de transação — mantido intacto, mas não
# renderizado por padrão (ver SHOW_TRANSACTION_FORM no topo do arquivo).
_FORM_SECTION_HTML = """<div class="chart-card" style="margin-top: 20px;">
    <div class="chart-head"><div class="chart-title">➕ Registrar compra ou venda</div></div>

    <div id="token-setup" class="token-setup" style="display:none;">
      <p>
        Cole um token do GitHub para salvar direto por aqui (crie em
        <a href="https://github.com/settings/personal-access-tokens/new" target="_blank" rel="noopener">github.com/settings/personal-access-tokens/new</a>,
        tipo <em>fine-grained</em>, restrito a este repositório, com permissão
        "Contents: Read and write" — e "Actions: Read and write" se quiser que o botão
        também recalcule na hora). Fica salvo só neste navegador (localStorage), nunca é
        enviado a nenhum lugar além da API do GitHub.
      </p>
      <div class="token-row">
        <input type="password" id="gh-token-input" placeholder="github_pat_...">
        <button type="button" class="btn btn-primary" id="gh-token-save">Salvar token</button>
      </div>
    </div>

    <form id="tx-form">
      <div class="field-grid">
        <div class="field">
          <label for="tx-date">Data</label>
          <input type="date" id="tx-date" required aria-describedby="tx-date-error">
          <span class="field-error" id="tx-date-error">Informe uma data.</span>
        </div>
        <div class="field">
          <label for="tx-ticker">Ticker</label>
          <select id="tx-ticker" required></select>
        </div>
        <div class="field">
          <label for="tx-action">Ação</label>
          <select id="tx-action" required>
            <option value="compra">Compra</option>
            <option value="venda">Venda</option>
          </select>
        </div>
        <div class="field">
          <label for="tx-qty">Quantidade</label>
          <input type="number" id="tx-qty" min="1" step="1" required aria-describedby="tx-qty-error">
          <span class="field-error" id="tx-qty-error">Informe uma quantidade maior que zero.</span>
        </div>
        <div class="field">
          <label for="tx-price">Preço médio</label>
          <input type="number" id="tx-price" min="0.01" step="0.01" required aria-describedby="tx-price-error">
          <span class="field-error" id="tx-price-error">Informe um preço maior que zero.</span>
        </div>
        <div class="field">
          <button type="submit" class="btn btn-primary">Salvar</button>
        </div>
      </div>
    </form>
    <div id="tx-status" role="status" aria-live="polite"></div>
    <p class="token-change">
      <a href="#" id="gh-token-change">Trocar ou remover o token salvo neste navegador</a>
    </p>
  </div>"""

_FORM_SCRIPT_TEMPLATE = """const REPO_OWNER = "{repo_owner}";
const REPO_NAME = "{repo_name}";
const FILE_PATH = "{file_path}";
const BRANCH = "{branch}";

// --- Formulário de nova transação (grava direto na API do GitHub) ---

const tickerSelect = document.getElementById('tx-ticker');
dados.composicao.forEach(a => {{
  const opt = document.createElement('option');
  opt.value = a.ticker;
  opt.textContent = a.ticker;
  tickerSelect.appendChild(opt);
}});
document.getElementById('tx-date').value = new Date().toISOString().slice(0, 10);

function ghToken() {{ return localStorage.getItem('gh_token') || ''; }}
function setGhToken(t) {{ localStorage.setItem('gh_token', t); }}
function clearGhToken() {{ localStorage.removeItem('gh_token'); }}

function refreshTokenUi() {{
  document.getElementById('token-setup').style.display = ghToken() ? 'none' : 'block';
}}
refreshTokenUi();

document.getElementById('gh-token-save').addEventListener('click', () => {{
  const v = document.getElementById('gh-token-input').value.trim();
  if (v) {{ setGhToken(v); refreshTokenUi(); }}
}});
document.getElementById('gh-token-change').addEventListener('click', (e) => {{
  e.preventDefault();
  clearGhToken();
  document.getElementById('gh-token-input').value = '';
  refreshTokenUi();
}});

async function ghApi(path, options) {{
  options = options || {{}};
  const headers = Object.assign({{
    'Authorization': 'Bearer ' + ghToken(),
    'Accept': 'application/vnd.github+json',
  }}, options.headers || {{}});
  const res = await fetch('https://api.github.com' + path, Object.assign({{ cache: 'no-store' }}, options, {{ headers }}));
  if (!res.ok) {{
    const body = await res.text();
    throw new Error('GitHub API ' + res.status + ': ' + body);
  }}
  return res.status === 204 ? null : res.json();
}}

async function appendTransaction(line, attempt) {{
  attempt = attempt || 1;
  const current = await ghApi('/repos/' + REPO_OWNER + '/' + REPO_NAME + '/contents/' + FILE_PATH + '?ref=' + BRANCH);
  const content = decodeURIComponent(escape(atob(current.content.replace(/\\n/g, ''))));
  const newContent = content.replace(/\\n+$/, '') + '\\n' + line + '\\n';
  const encoded = btoa(unescape(encodeURIComponent(newContent)));
  try {{
    await ghApi('/repos/' + REPO_OWNER + '/' + REPO_NAME + '/contents/' + FILE_PATH, {{
      method: 'PUT',
      body: JSON.stringify({{
        message: 'chore: registra transação via dashboard',
        content: encoded,
        sha: current.sha,
        branch: BRANCH,
      }}),
    }});
  }} catch (err) {{
    // conflito de escrita (409): o arquivo mudou entre o GET e o PUT — busca de novo e tenta mais uma vez
    if (attempt < 3 && String(err.message).includes('409')) {{
      return appendTransaction(line, attempt + 1);
    }}
    throw err;
  }}
}}

async function triggerWorkflow() {{
  try {{
    await ghApi('/repos/' + REPO_OWNER + '/' + REPO_NAME + '/actions/workflows/monitor.yml/dispatches', {{
      method: 'POST',
      body: JSON.stringify({{ ref: BRANCH }}),
    }});
    return true;
  }} catch (e) {{
    return false;
  }}
}}

function validarCampo(input, errorEl, invalido) {{
  input.setAttribute('aria-invalid', invalido ? 'true' : 'false');
  if (errorEl) errorEl.classList.toggle('show', invalido);
}}

document.getElementById('tx-form').addEventListener('submit', async (e) => {{
  e.preventDefault();
  const statusEl = document.getElementById('tx-status');
  const dateEl = document.getElementById('tx-date');
  const qtyEl = document.getElementById('tx-qty');
  const priceEl = document.getElementById('tx-price');

  const date = dateEl.value;
  const ticker = document.getElementById('tx-ticker').value;
  const action = document.getElementById('tx-action').value;
  const qty = qtyEl.value;
  const price = priceEl.value;

  validarCampo(dateEl, document.getElementById('tx-date-error'), !date);
  validarCampo(qtyEl, document.getElementById('tx-qty-error'), !qty || Number(qty) <= 0);
  validarCampo(priceEl, document.getElementById('tx-price-error'), !price || Number(price) <= 0);

  if (!date || !ticker || !qty || !price || Number(qty) <= 0 || Number(price) <= 0) {{
    statusEl.textContent = 'Preencha todos os campos com valores válidos.';
    return;
  }}
  if (!ghToken()) {{
    statusEl.textContent = 'Configure o token do GitHub primeiro.';
    return;
  }}

  const line = [date, ticker, action, qty, Number(price).toFixed(2)].join(',');
  const submitBtn = e.target.querySelector('button[type="submit"]');
  submitBtn.disabled = true;
  statusEl.textContent = 'Salvando...';
  try {{
    await appendTransaction(line);
    let msg = 'Transação registrada!';
    const dispatched = await triggerWorkflow();
    msg += dispatched
      ? ' Recalculando agora — atualiza em alguns minutos.'
      : ' Vai refletir na próxima execução automática (a cada 30min no pregão, ou 1x/dia pro dashboard).';
    statusEl.textContent = msg;
    e.target.reset();
    document.getElementById('tx-date').value = new Date().toISOString().slice(0, 10);
  }} catch (err) {{
    statusEl.textContent = 'Erro ao salvar: ' + err.message;
  }} finally {{
    submitBtn.disabled = false;
  }}
}});"""


def build_dashboard_html(
    statuses: list[AssetStatus],
    wealth_history: list[dict],
    monthly_returns: list[MonthlyReturn],
    generated_at: str,
) -> str:
    """`wealth_history` é a série acumulada dia a dia (ver
    config.load_wealth_history) — cada linha tem date/wealth/invested/
    nominal_return/real_return como strings (vindas do CSV), usada só pro
    gráfico de patrimônio. `monthly_returns` (ver
    performance.compute_monthly_returns) é o retorno de cada mês
    isoladamente — usado no gráfico de barras de performance mensal."""
    dados = {
        "composicao": [
            {
                "ticker": s.ticker,
                "pct": round(s.pct * 100, 2),
                "alvo": round(s.target.target * 100, 2),
                "min": round(s.target.min * 100, 2),
                "max": round(s.target.max * 100, 2),
                "status": s.status,
            }
            for s in statuses
        ],
        "patrimonio": [{"data": r["date"], "valor": round(float(r["wealth"]), 2)} for r in wealth_history],
        "performance": [
            {
                "mes": f"{MES_ABREV[m.month]}/{m.year}",
                "nominal": round(m.nominal * 100, 2) if m.nominal is not None else None,
                "real": round(m.real * 100, 2) if m.real is not None else None,
            }
            for m in monthly_returns
        ],
    }
    ultimo = wealth_history[-1] if wealth_history else None

    def _fmt_brl(v: float) -> str:
        return f"R$ {v:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")

    if ultimo is None:
        kpi_tiles = [
            ("Patrimônio atual", "—", ""),
            ("Total investido", "—", ""),
        ]
    else:
        kpi_tiles = [
            ("Patrimônio atual", _fmt_brl(float(ultimo["wealth"])), ""),
            ("Total investido", _fmt_brl(float(ultimo["invested"])), ""),
        ]
    kpi_section = '<div class="kpi-row">\n' + "\n".join(
        f'    <div class="kpi-tile"><div class="kpi-label">{label}</div>'
        f'<div class="kpi-value {cls}">{value}</div></div>'
        for label, value, cls in kpi_tiles
    ) + "\n  </div>"

    if SHOW_TRANSACTION_FORM:
        form_section = _FORM_SECTION_HTML
        form_script = _FORM_SCRIPT_TEMPLATE.format(
            repo_owner=REPO_OWNER,
            repo_name=REPO_NAME,
            file_path=FILE_PATH,
            branch=BRANCH,
        )
    else:
        form_section = ""
        form_script = ""

    return _TEMPLATE.format(
        generated_at=generated_at,
        dados_json=json.dumps(dados, ensure_ascii=False),
        kpi_section=kpi_section,
        form_section=form_section,
        form_script=form_script,
    )
