"""Decide se um disparo do `schedule` (backup esparso, 1x/hora) do GitHub
Actions deve ser pulado por já ter havido uma execução recente — via
cron-job.org chamando `workflow_dispatch` a cada 15min.

Só o `schedule` é tratado como redundante aqui: um `workflow_dispatch`
(manual ou do cron-job.org) sempre roda. Isso é o que faz o `schedule` ser
de fato um *fallback* — ele só executa o job quando o cron externo realmente
parou de disparar, não incondicionalmente toda hora.

Escreve `pular=true`/`pular=false` em $GITHUB_OUTPUT para os steps
seguintes do workflow decidirem se rodam.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# Se a última execução (de qualquer origem) foi há menos que isso, o
# disparo do `schedule` é redundante: o cron externo de 15min já deve ter
# coberto essa janela recentemente.
LIMIAR_REDUNDANCIA_MINUTOS = 12


def main(argv: list[str]) -> int:
    nome_fluxo = argv[1] if len(argv) > 1 else "desvio"
    last_run_path = REPO_ROOT / "config" / f"last_run_{nome_fluxo}_at.txt"

    pular = False
    if os.environ.get("GITHUB_EVENT_NAME") == "schedule" and last_run_path.exists():
        ultima_execucao = datetime.fromisoformat(
            last_run_path.read_text(encoding="utf-8").strip()
        )
        gap_minutos = (datetime.now(timezone.utc) - ultima_execucao).total_seconds() / 60
        pular = gap_minutos < LIMIAR_REDUNDANCIA_MINUTOS

    valor = "true" if pular else "false"
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as fh:
            fh.write(f"pular={valor}\n")

    print(f"pular={valor}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
