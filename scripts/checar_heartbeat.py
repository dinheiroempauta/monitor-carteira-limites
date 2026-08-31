"""Detecta se os gatilhos de um fluxo (cron-job.org + fallback `schedule`
do GitHub) pararam de disparar.

Recebe o nome do fluxo como argumento (`aportes` ou `desvio` — ver
monitor_aportes.yml e monitor_desvio.yml) porque cada um agora é um
workflow independente, com seu próprio cron externo e seu próprio arquivo
de heartbeat — uma falha no disparo de um não deve mascarar nem ser
mascarada pela do outro.

A cadência normal (15min) vem de um cron externo (cron-job.org) chamando
`workflow_dispatch` — não depende do agendador do GitHub. O `schedule`
nativo do GitHub Actions é só o backup esparso (1x/hora): não é garantido,
pode atrasar ou ser descartado silenciosamente em picos de carga. O que dá
pra fazer é notar, na primeira execução que *conseguir* rodar (de
qualquer uma das duas origens), que faz tempo demais desde a última — e
avisar no Telegram em vez de deixar passar batido (ex.: se o cron-job.org
parar de funcionar e o fallback horário também atrasar).

Guarda o timestamp da última execução em config/last_run_<fluxo>_at.txt.
Só alerta se: (a) já existe um timestamp anterior, (b) o gap desde ele é
maior que o esperado, e (c) estamos dentro do horário de mercado (pra não
disparar falso alarme depois de uma noite/fim de semana sem cron).
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from monitor.telegram import TelegramSendError, send_message

REPO_ROOT = Path(__file__).resolve().parents[1]

# O monitor dispara a cada 15min das 7h-18h BRT (10h-21h UTC), dias úteis,
# via cron-job.org. Um gap maior que isso durante essa janela indica que
# o cron externo (e possivelmente o fallback horário do GitHub também)
# deixaram de disparar.
#
# O início real do cron-job.org é ~10h UTC (7h BRT) — antes disso só o
# fallback horário do GitHub roda, e cada disparo dele calcularia um gap
# de ~60min (> GAP_LIMIT_MINUTOS) contra a execução do dia anterior,
# gerando alerta falso logo cedo. Por isso a janela começa em 10h UTC, e
# não em 9h UTC.
GAP_LIMIT_MINUTOS = 40
HORA_INICIO_UTC = 10
HORA_FIM_UTC = 21


def _dentro_do_horario_de_mercado(agora: datetime) -> bool:
    return agora.weekday() < 5 and HORA_INICIO_UTC <= agora.hour <= HORA_FIM_UTC


def main(argv: list[str]) -> int:
    nome_fluxo = argv[1] if len(argv) > 1 else "desvio"
    last_run_path = REPO_ROOT / "config" / f"last_run_{nome_fluxo}_at.txt"

    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    agora = datetime.now(timezone.utc)
    ultima_execucao_str = last_run_path.read_text(encoding="utf-8").strip() if last_run_path.exists() else None

    if ultima_execucao_str and _dentro_do_horario_de_mercado(agora):
        ultima_execucao = datetime.fromisoformat(ultima_execucao_str)
        gap_minutos = (agora - ultima_execucao).total_seconds() / 60
        if gap_minutos > GAP_LIMIT_MINUTOS and bot_token and chat_id:
            try:
                send_message(
                    f"⚠️ *Monitoria de {nome_fluxo}*: o agendamento automático do GitHub Actions "
                    f"ficou {gap_minutos:.0f} minutos sem disparar durante o horário de mercado "
                    "(esperado a cada 15min). Isso é uma falha conhecida do `schedule` do GitHub "
                    "(descarte silencioso em picos de carga), não do código — mas vale checar a "
                    "aba Actions se isso persistir.",
                    bot_token,
                    chat_id,
                    parse_mode="Markdown",
                )
            except TelegramSendError as exc:
                print(f"Falha ao enviar alerta de heartbeat: {exc}", file=sys.stderr)

    last_run_path.write_text(agora.isoformat(timespec="seconds"), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
