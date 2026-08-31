"""Detecta se os gatilhos de um fluxo (cron-job.org + fallback `schedule`
do GitHub) pararam de disparar.

Recebe o nome do fluxo como argumento (`aportes` ou `desvio` — ver
monitor_aportes.yml e monitor_desvio.yml) porque cada um agora é um
workflow independente, com seu próprio cron externo e seu próprio arquivo
de heartbeat — uma falha no disparo de um não deve mascarar nem ser
mascarada pela do outro.

IMPORTANTE: os dois fluxos rodam em janelas de horário DIFERENTES e não
sobrepostas, por design — não é um horário "de mercado" único:
- aportes: cron-job.org roda `*/15 4-9 * * 1-5` (BRT) = 7h-12h UTC. Importa
  notas de corretagem por e-mail antes da abertura do pregão.
- desvio: cron-job.org roda `*/15 10-18 * * 1-5` (BRT) = 13h-21h UTC.
  Monitora desvio de banda durante o pregão.
Por isso cada fluxo tem sua própria janela de checagem aqui — comparar os
dois com uma janela só gera alerta falso (o fluxo aparenta "atrasado" só
por estar fora da janela dele, quando na verdade está corretamente
parado).

A cadência normal (15min) vem de um cron externo (cron-job.org) chamando
`workflow_dispatch` — não depende do agendador do GitHub. O `schedule`
nativo do GitHub Actions é só o backup esparso (1x/hora), configurado para
a mesma janela do cron externo de cada fluxo (ver monitor_aportes.yml e
monitor_desvio.yml): não é garantido, pode atrasar ou ser descartado
silenciosamente em picos de carga. O que dá pra fazer é notar, na primeira
execução que *conseguir* rodar (de qualquer uma das duas origens), que faz
tempo demais desde a última — e avisar no Telegram em vez de deixar passar
batido (ex.: se o cron-job.org parar de funcionar e o fallback horário
também atrasar).

Guarda o timestamp da última execução em config/last_run_<fluxo>_at.txt.
Só alerta se: (a) já existe um timestamp anterior, (b) o gap desde ele é
maior que o esperado, (c) estamos dentro da janela daquele fluxo, e (d) não
estamos nos primeiros minutos da janela (evita alarme falso todo dia,
comparando com o horário de fechamento do dia anterior).
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from monitor.telegram import TelegramSendError, send_message

REPO_ROOT = Path(__file__).resolve().parents[1]

GAP_LIMIT_MINUTOS = 40

# Janela de cada fluxo em horas UTC (início inclusivo, fim inclusivo),
# espelhando o cron externo no cron-job.org.
JANELAS_UTC = {
    "aportes": (7, 12),   # */15 4-9 * * 1-5 (BRT)
    "desvio": (13, 21),   # */15 10-18 * * 1-5 (BRT)
}

# Nos primeiros minutos da janela, não alerta: o "gap" ali é só a distância
# até o fim da janela do dia anterior (ou do fim de semana), não uma falha.
MINUTOS_DE_FOLGA_NO_INICIO_DA_JANELA = 20


def _janela_do_fluxo(nome_fluxo: str) -> tuple[int, int]:
    return JANELAS_UTC.get(nome_fluxo, (7, 21))


def _dentro_da_janela(agora: datetime, nome_fluxo: str) -> bool:
    hora_inicio, hora_fim = _janela_do_fluxo(nome_fluxo)
    return agora.weekday() < 5 and hora_inicio <= agora.hour <= hora_fim


def _no_inicio_da_janela(agora: datetime, nome_fluxo: str) -> bool:
    hora_inicio, _ = _janela_do_fluxo(nome_fluxo)
    return agora.hour == hora_inicio and agora.minute < MINUTOS_DE_FOLGA_NO_INICIO_DA_JANELA


def main(argv: list[str]) -> int:
    nome_fluxo = argv[1] if len(argv) > 1 else "desvio"
    last_run_path = REPO_ROOT / "config" / f"last_run_{nome_fluxo}_at.txt"

    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    agora = datetime.now(timezone.utc)
    ultima_execucao_str = last_run_path.read_text(encoding="utf-8").strip() if last_run_path.exists() else None

    deve_checar = (
        ultima_execucao_str
        and _dentro_da_janela(agora, nome_fluxo)
        and not _no_inicio_da_janela(agora, nome_fluxo)
    )
    if deve_checar:
        ultima_execucao = datetime.fromisoformat(ultima_execucao_str)
        gap_minutos = (agora - ultima_execucao).total_seconds() / 60
        if gap_minutos > GAP_LIMIT_MINUTOS and bot_token and chat_id:
            try:
                send_message(
                    f"⚠️ *Monitoria de {nome_fluxo}*: o agendamento automático do GitHub Actions "
                    f"ficou {gap_minutos:.0f} minutos sem disparar durante a janela ativa deste fluxo "
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
