# HEARTBEAT.md — Configuração de Heartbeats

## Frequência
A cada **2h**

## O que checar
- Compromissos nas próximas 24-48h
- Crons — todos rodaram?
- Emails urgentes

## Horários
- **Silêncio (não rodar):** 23:00 — 08:00
- **Foco (não interromper):** 09:00 — 12:00
- **Melhor pra notificações:** 08:00 — 10:00

## Modelo
Claude Haiku (~R$0,04 por heartbeat)

## Template de Heartbeat
```
[HEARTBEAT 2h] Checagem automática:
1. Compromissos próximas 48h
2. Status dos crons
3. Items selecionados pelo usuário
4. Ações pendentes

Reportar apenas se houver algo relevante.
Se nada urgente, log silencioso.
```

---
*Gerado pelo Configurador da Clawdete — Workshop OpenClaw Brasil 🦞*
