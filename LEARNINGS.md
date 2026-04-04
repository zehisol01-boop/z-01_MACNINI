# LEARNINGS.md — Regras e Lições Aprendidas

## Como usar este arquivo
Registro central de regras operacionais, padrões confirmados e lições aprendidas.
Consultar antes de iniciar qualquer tarefa relevante.
Atualizado automaticamente toda noite às 02:00 via cron.

---

## Regras Operacionais

- **Sempre responder em português** — Sergio prefere PT-BR em todas as interações
- **Confirmar antes de enviar externamente** — emails, WhatsApp, mensagens para terceiros precisam de aprovação
- **Não elogiar desnecessariamente** — sem "Ótima pergunta!", direto ao ponto
- **ClawHub flagou skill-creator como suspeito** — instalar só com --force e confirmação do Sergio

## Padrões Confirmados

### Infraestrutura
- Mac Mini em casa (Windermere FL) — IP 10.50.0.121
- OpenClaw via Telegram — canal principal de comunicação
- Roteador MikroTik RB760iGS — SNMP community: HISOL
- WAN2: UP | WAN1: DOWN (verificar status)
- Backup GitHub diário às 03:00 AM (cron ID: 973573f3)

### Providers de IA ativos
- **Anthropic** direto — provider principal (Claude Sonnet 4.6)
- **OpenRouter** — 345 modelos, chave configurada
- **Abacus RouteLLM** — 123 modelos, fallback chain configurado

### Ferramentas instaladas
- ClawHub v0.9.0 — instalado globalmente via npm
- Obsidian — desinstalado em 02/04/2026 (a pedido do Sergio)
- Aulas OpenClaw salvas em ~/Documents/OpenClaw-Aulas (8 módulos, .md)

### Imóvel 502 W Lester Rd, Apopka FL
- Parcel ID: 33-20-28-0000-00-084
- ~10 acres, equestrian estate, sem HOA
- Vendido em jul/2025 por $1,100,000 (listagem: $1,295,000)
- **Sewer**: FORA do Orange County sewer district — sem linha na Lester Rd
- **Water**: disponível na propriedade (sprinkler 6 zonas, barn)
- Zoning exato: confirmar via (407) 836-5044
- Utility Availability Letter: solicitar em ocfl.net/Utilities/Developers.aspx

## Lições Aprendidas

- **GIS do Orange County** usa JavaScript dinâmico — portal OCPA não funciona via web_fetch. Usar API REST do ArcGIS diretamente (gis.orangecountygov.com/arcgis/rest/services)
- **Sewer District query** retornou `features: []` = lote fora da área de serviço
- **Realtor.com** bloqueia web_fetch (429). Compass.com funciona melhor para dados de imóveis

---

## Pendências em aberto
- [ ] WAN1 do roteador HISOL-WINDERMERE — verificar status
- [ ] Zoning exato do 502 W Lester Rd — ligar (407) 836-5044
- [ ] Utility Availability Letter — solicitar em ocfl.net/Utilities/Developers.aspx
- [ ] Criar skills customizadas Hisol (proposta, NOC, evento)
- [ ] Configurar modelo mais barato para crons (gemini-2.5-flash ou deepseek-r1)

---
*Gerenciado pela ZE 🧠 — atualizado automaticamente*
