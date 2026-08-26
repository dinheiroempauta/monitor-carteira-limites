"""Detecta se o disparo `schedule` do GitHub Actions parou de rodar.

Não temos como forçar o GitHub a executar um workflow que ele mesmo não
disparou (limitação conhecida e documentada: eventos `schedule` podem
atrasar ou ser descartados silenciosamente em picos de carga — ver
.github/workflows/monitor.yml). O que dá pra fazer é notar, na primeira
execução que *conseguir* rodar, que faz tempo demais desde a última — e
avisar no Telegram em vez de deixar passar batido.

Guarda o timestamp da última execução em config/last_run_at.txt. Só
alerta se: (a) já existe um timestamp anterior, (b) o gap desde ele é
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
LAST_RUN_PATH = REPO_ROOT / "config" / "last_run_at.txt"

# O monitor de bandas dispara a cada 15min das 13h-21h UTC (dias úteis) —
# ver monitor.yml. Um gap maior que isso durante essa janela indica que
# um ou mais disparos foram perdidos.
GAP_LIMIT_MINUTOS = 40
HORA_INICIO_UTC = 13
HORA_FIM_UTC = 21


def _dentro_do_horario_de_mercado(agora: datetime) -> bool:
    return agora.weekday() < 5 and HORA_INICIO_UTC <= agora.hour <= HORA_FIM_UTC


def main() -> int:
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    agora = datetime.now(timezone.utc)
    ultima_execucao_str = LAST_RUN_PATH.read_text(encoding="utf-8").strip() if LAST_RUN_PATH.exists() else None

    if ultima_execucao_str and _dentro_do_horario_de_mercado(agora):
        ultima_execucao = datetime.fromisoformat(ultima_execucao_str)
        gap_minutos = (agora - ultima_execucao).total_seconds() / 60
        if gap_minutos > GAP_LIMIT_MINUTOS and bot_token and chat_id:
            try:
                send_message(
                    "⚠️ *Monitor de Carteira*: o agendamento automático do GitHub Actions "
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

    LAST_RUN_PATH.write_text(agora.isoformat(timespec="seconds"), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
