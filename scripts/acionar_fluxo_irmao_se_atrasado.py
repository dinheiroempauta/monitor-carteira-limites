"""Aciona o workflow "irmão" (aportes <-> desvio) via `workflow_dispatch`
quando o heartbeat dele está atrasado.

Contexto: cada monitoria (aportes, desvio) tem seu próprio job no cron
externo (cron-job.org) chamando `workflow_dispatch` a cada 15min, com um
fallback nativo do GitHub (`schedule`) rodando só 1x/hora caso o cron
externo falhe. Mas se o cron externo de UM dos dois fluxos parar (e só
dele — o outro continua saudável), o único jeito de perceber era esperar
até 1h pelo fallback horário do GitHub, gerando um atraso real no serviço
e um alerta de heartbeat só depois de 40min sem rodar.

Este script usa a cadência saudável de um fluxo (ex.: desvio, cujo cron
externo está rodando normalmente a cada 15min) para checar a saúde do
fluxo irmão (ex.: aportes) e, se ele estiver atrasado, aciona o
`workflow_dispatch` dele imediatamente — uma segunda rede de segurança
bem mais rápida que o fallback horário nativo, e que não depende de
credencial nenhuma além do GITHUB_TOKEN padrão da própria Action.

Roda sempre (mesmo em disparos considerados redundantes pelo próprio
fluxo) porque o objetivo aqui é checar o IRMÃO, não decidir se este
fluxo deve executar seu próprio trabalho.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# Menor que o GAP_LIMIT_MINUTOS do checar_heartbeat.py (40min) — a ideia é
# tentar resolver acionando o irmão antes que o atraso vire alerta no
# Telegram.
LIMIAR_ATRASO_MINUTOS = 20
HORA_INICIO_UTC = 10
HORA_FIM_UTC = 21


def _dentro_do_horario_de_mercado(agora: datetime) -> bool:
    return agora.weekday() < 5 and HORA_INICIO_UTC <= agora.hour <= HORA_FIM_UTC


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print("uso: acionar_fluxo_irmao_se_atrasado.py <nome_fluxo> <arquivo_workflow.yml>", file=sys.stderr)
        return 1

    nome_fluxo_alvo, arquivo_workflow_alvo = argv[1], argv[2]
    last_run_path = REPO_ROOT / "config" / f"last_run_{nome_fluxo_alvo}_at.txt"

    agora = datetime.now(timezone.utc)
    if not last_run_path.exists() or not _dentro_do_horario_de_mercado(agora):
        return 0

    ultima_execucao = datetime.fromisoformat(last_run_path.read_text(encoding="utf-8").strip())
    gap_minutos = (agora - ultima_execucao).total_seconds() / 60
    if gap_minutos <= LIMIAR_ATRASO_MINUTOS:
        return 0

    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not token or not repo:
        return 0

    url = f"https://api.github.com/repos/{repo}/actions/workflows/{arquivo_workflow_alvo}/dispatches"
    body = json.dumps({"ref": "main"}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        urllib.request.urlopen(req, timeout=15)
        print(f"Acionado {arquivo_workflow_alvo}: heartbeat de '{nome_fluxo_alvo}' atrasado {gap_minutos:.0f}min")
    except urllib.error.HTTPError as exc:
        print(f"Falha ao acionar {arquivo_workflow_alvo}: HTTP {exc.code} {exc.read().decode(errors='replace')}", file=sys.stderr)
    except urllib.error.URLError as exc:
        print(f"Falha ao acionar {arquivo_workflow_alvo}: {exc}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
