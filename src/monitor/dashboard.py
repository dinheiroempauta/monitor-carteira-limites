"""Monta a página HTML do dashboard de performance (Chart.js via CDN —
publicada no GitHub Pages, que não tem as restrições de CSP dos Artifacts).

Inclui um formulário que registra novas transações direto do navegador,
via API do GitHub (token fine-grained salvo só no localStorage do usuário
— nunca enviado a nenhum outro lugar além de api.github.com)."""
from __future__ import annotations

import json

from monitor.allocation import AssetStatus

REPO_OWNER = "dinheiroempauta"
REPO_NAME = "monitor-carteira-limites"
FILE_PATH = "config/transactions.csv"
BRANCH = "main"

_TEMPLATE = r"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Performance da Carteira</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<style>
  :root {{
    color-scheme: light dark;
    --bg: #ffffff; --fg: #1a1a1a; --card: #f5f5f7; --border: #e0e0e0; --accent: #4f7cff;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{ --bg: #14151a; --fg: #e8e8ea; --card: #1e1f26; --border: #2c2d36; }}
  }}
  body {{
    background: var(--bg); color: var(--fg); margin: 0; padding: 24px;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  }}
  h1 {{ font-size: 1.4rem; margin-bottom: 4px; }}
  .atualizado {{ opacity: 0.6; font-size: 0.85rem; margin-bottom: 24px; }}
  .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
  @media (max-width: 800px) {{ .grid {{ grid-template-columns: 1fr; }} }}
  .card {{
    background: var(--card); border: 1px solid var(--border); border-radius: 12px;
    padding: 16px; min-width: 0;
  }}
  .card h2 {{ font-size: 1rem; margin: 0 0 12px; }}
  .full {{ grid-column: 1 / -1; }}
  canvas {{ max-width: 100%; }}
  label {{ display: flex; flex-direction: column; gap: 4px; font-size: 0.8rem; opacity: 0.85; }}
  input, select, button {{
    font: inherit; padding: 8px; border-radius: 8px; border: 1px solid var(--border);
    background: var(--bg); color: var(--fg);
  }}
  button {{ background: var(--accent); color: #fff; border: none; cursor: pointer; }}
  button:disabled {{ opacity: 0.5; cursor: default; }}
  a {{ color: var(--accent); }}
  #tx-status {{ min-height: 1.2em; }}
</style>
</head>
<body>
<h1>📊 Performance da Carteira</h1>
<div class="atualizado">Atualizado em {generated_at} — patrimônio e performance acumulam a partir do dia em que o dashboard começou a rodar, sem reconstruir o passado.</div>

<div class="grid">
  <div class="card">
    <h2>Composição atual</h2>
    <canvas id="composicao"></canvas>
  </div>
  <div class="card full">
    <h2>Patrimônio ao longo do tempo</h2>
    <canvas id="patrimonio"></canvas>
  </div>
  <div class="card full">
    <h2>Performance nominal vs. real (descontada a inflação)</h2>
    <canvas id="performance"></canvas>
  </div>

  <div class="card full">
    <h2>➕ Registrar compra ou venda</h2>

    <div id="token-setup" style="display:none; margin-bottom:14px;">
      <p style="font-size:0.85rem; opacity:0.8; margin-top:0;">
        Cole um token do GitHub para salvar direto por aqui (crie em
        <a href="https://github.com/settings/personal-access-tokens/new" target="_blank" rel="noopener">github.com/settings/personal-access-tokens/new</a>,
        tipo <em>fine-grained</em>, restrito a este repositório, com permissão
        "Contents: Read and write" — e "Actions: Read and write" se quiser que o botão
        também recalcule na hora). Fica salvo só neste navegador (localStorage), nunca é
        enviado a nenhum lugar além da API do GitHub.
      </p>
      <div style="display:flex; gap:8px;">
        <input type="password" id="gh-token-input" placeholder="github_pat_..." style="flex:1;">
        <button type="button" id="gh-token-save">Salvar token</button>
      </div>
    </div>

    <form id="tx-form" style="display:grid; grid-template-columns: repeat(auto-fit, minmax(110px,1fr)); gap:10px; align-items:end;">
      <label>Data
        <input type="date" id="tx-date" required>
      </label>
      <label>Ticker
        <select id="tx-ticker" required></select>
      </label>
      <label>Ação
        <select id="tx-action" required>
          <option value="compra">Compra</option>
          <option value="venda">Venda</option>
        </select>
      </label>
      <label>Quantidade
        <input type="number" id="tx-qty" min="1" step="1" required>
      </label>
      <label>Preço médio
        <input type="number" id="tx-price" min="0.01" step="0.01" required>
      </label>
      <button type="submit">Salvar</button>
    </form>
    <div id="tx-status" style="margin-top:10px; font-size:0.9rem;"></div>
    <p style="font-size:0.8rem; opacity:0.6; margin-top:12px;">
      <a href="#" id="gh-token-change">Trocar ou remover o token salvo neste navegador</a>
    </p>
  </div>
</div>

<script>
const dados = {dados_json};
const REPO_OWNER = "{repo_owner}";
const REPO_NAME = "{repo_name}";
const FILE_PATH = "{file_path}";
const BRANCH = "{branch}";

new Chart(document.getElementById('composicao'), {{
  type: 'doughnut',
  data: {{
    labels: dados.composicao.map(a => a.ticker),
    datasets: [{{ data: dados.composicao.map(a => a.pct) }}]
  }},
  options: {{
    plugins: {{ tooltip: {{ callbacks: {{ label: c => `${{c.label}}: ${{c.raw.toFixed(1)}}%` }} }} }}
  }}
}});

new Chart(document.getElementById('patrimonio'), {{
  type: 'line',
  data: {{
    labels: dados.patrimonio.map(p => p.data),
    datasets: [{{ label: 'Patrimônio (R$)', data: dados.patrimonio.map(p => p.valor), borderColor: '#4f7cff', tension: 0.15 }}]
  }}
}});

new Chart(document.getElementById('performance'), {{
  type: 'line',
  data: {{
    labels: dados.performance.map(p => p.data),
    datasets: [
      {{ label: 'Nominal', data: dados.performance.map(p => p.nominal), borderColor: '#4f7cff', tension: 0.15 }},
      {{ label: 'Real (descontado IPCA)', data: dados.performance.map(p => p.real), borderColor: '#ff8a4f', tension: 0.15 }}
    ]
  }},
  options: {{
    plugins: {{ tooltip: {{ callbacks: {{ label: c => `${{c.dataset.label}}: ${{c.raw?.toFixed(2)}}%` }} }} }},
    scales: {{ y: {{ ticks: {{ callback: v => v + '%' }} }} }}
  }}
}});

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
  const content = decodeURIComponent(escape(atob(current.content.replace(/\n/g, ''))));
  const newContent = content.replace(/\n+$/, '') + '\n' + line + '\n';
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

document.getElementById('tx-form').addEventListener('submit', async (e) => {{
  e.preventDefault();
  const statusEl = document.getElementById('tx-status');
  if (!ghToken()) {{
    statusEl.textContent = '⚠️ Configure o token do GitHub primeiro.';
    return;
  }}
  const date = document.getElementById('tx-date').value;
  const ticker = document.getElementById('tx-ticker').value;
  const action = document.getElementById('tx-action').value;
  const qty = document.getElementById('tx-qty').value;
  const price = document.getElementById('tx-price').value;
  if (!date || !ticker || !qty || !price || Number(qty) <= 0 || Number(price) <= 0) {{
    statusEl.textContent = '⚠️ Preencha todos os campos com valores válidos.';
    return;
  }}
  const line = [date, ticker, action, qty, Number(price).toFixed(2)].join(',');
  const submitBtn = e.target.querySelector('button[type="submit"]');
  submitBtn.disabled = true;
  statusEl.textContent = 'Salvando...';
  try {{
    await appendTransaction(line);
    let msg = '✅ Transação registrada!';
    const dispatched = await triggerWorkflow();
    msg += dispatched
      ? ' Recalculando agora — atualiza em alguns minutos.'
      : ' Vai refletir na próxima execução automática (a cada 30min no pregão, ou 1x/dia pro dashboard).';
    statusEl.textContent = msg;
    e.target.reset();
    document.getElementById('tx-date').value = new Date().toISOString().slice(0, 10);
  }} catch (err) {{
    statusEl.textContent = '❌ Erro ao salvar: ' + err.message;
  }} finally {{
    submitBtn.disabled = false;
  }}
}});
</script>
</body>
</html>
"""


def build_dashboard_html(
    statuses: list[AssetStatus],
    wealth_history: list[dict],
    generated_at: str,
) -> str:
    """`wealth_history` é a série acumulada dia a dia (ver
    config.load_wealth_history) — cada linha tem date/wealth/invested/
    nominal_return/real_return como strings (vindas do CSV)."""
    dados = {
        "composicao": [{"ticker": s.ticker, "pct": round(s.pct * 100, 2)} for s in statuses],
        "patrimonio": [{"data": r["date"], "valor": round(float(r["wealth"]), 2)} for r in wealth_history],
        "performance": [
            {
                "data": r["date"],
                "nominal": round(float(r["nominal_return"]) * 100, 2),
                "real": round(float(r["real_return"]) * 100, 2) if r["real_return"] not in ("", None) else None,
            }
            for r in wealth_history
        ],
    }
    return _TEMPLATE.format(
        generated_at=generated_at,
        dados_json=json.dumps(dados, ensure_ascii=False),
        repo_owner=REPO_OWNER,
        repo_name=REPO_NAME,
        file_path=FILE_PATH,
        branch=BRANCH,
    )
