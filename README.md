<div align="center">

# Bot de Correção de Polichinelos

**Um bot de Discord que transforma punições em tickets automáticos de contagem por extenso.**

![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![discord.py](https://img.shields.io/badge/discord.py-2.6%2B-5865F2?style=for-the-badge&logo=discord&logoColor=white)
![Components V2](https://img.shields.io/badge/Components-V2-2ECC71?style=for-the-badge)
![Status](https://img.shields.io/badge/status-ativo-success?style=for-the-badge)

[![Baixar](https://img.shields.io/badge/⬇_Baixar_o_bot-.zip-2ECC71?style=for-the-badge)](https://github.com/henriquew1133/Bot-para-corrigir-polichinelos/releases/latest/download/polichinelo-bot.zip)

</div>

---

## Funcionalidades do Bot

- **Tickets automáticos conforme a punição:** cada punição cria um canal privado, visível só para o punido, o bot e a equipe (definido por um comando).
- **Contagem por extenso:** `UM!`, `DOIS!`, `TRÊS!`, com acento e exclamação obrigatórios.
- **Painel ao vivo, atualizando a cada punição** com barra de progresso.
- **Erro = bloqueio de 5 segundos:** só o envio de mensagens é bloqueado.
- **Relatórios de punição e de finalização**: postados automaticamente, com comandos e o de finalização é automático.
---

## Como funciona

```text
 /punir  ou  relatório escrito por uma pessoa
                    │
                    ▼
        Cria um canal privado para a punição
                    │
                    ▼
   Punido envia: UM!  DOIS!  TRÊS!  até o total
        │                              │
     se errar                        terminou?
        │                              │
 Bloqueio de 5s             Acesso do punido removido
                                       │
                    Botões: [Enviar relatório] [Fechar canal]
```

---

## Instalação e Modo de Usar

### 1. Pré-Requisitos:

- Python **3.9+**
- `discord.py` **2.6+** (necessário para Components V2)

```bash
py -m pip install -U discord.py tzdata
```

> No Linux/macOS, use `python3 -m pip install -U discord.py tzdata`.

### 2. Token do bot

Use **uma** das opções:

| Opção | Como |
|---|---|
| Variável de ambiente | defina `TOKEN` com o token |
| Arquivo | crie `token.txt` na mesma pasta do `index.py`, só com o token dentro |

### 3. Developer Portal

Em **Bot → Privileged Gateway Intents**, ative **Message Content Intent**.

### 4. Permissões do bot

- Gerenciar Canais
- Gerenciar Permissões
- Ver Canais
- Enviar Mensagens
- Ler Histórico de Mensagens
- Adicionar Reações

---

## Configuração inicial para funcionamento ideal do bot:

Feita **uma única vez** por servidor:

| Comando | O que faz |
|---|---|
| `/equipe cargo:@cargo` | Define o cargo da equipe: vê os tickets, usa os botões e aplica punições |
| `/relatorio_punicao canal:#canal` | Define o canal do **Relatório de Punição!** (os tickets são criados na mesma categoria) |
| `/relatorio_finalizacao canal:#canal` | Define o canal do **Relatório de Finalização de Punição** |

---

## Personalização

As constantes no topo do `index.py` controlam diversos comportamentos:

```python
POLICHINELOS_MAXIMOS = 500   # limite por punição
LOCK_SECONDS = 5         # tempo de bloqueio ao errar
TZ = ZoneInfo("America/Sao_Paulo")  # fuso dos horários nos relatórios
```
---

Feito por **henriquew1133** · Discord: `mercurythebest`
