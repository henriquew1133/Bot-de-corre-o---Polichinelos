import asyncio
import contextlib
import json
import os
import re
import unicodedata
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import discord
from discord import app_commands
from discord.ext import commands

if not hasattr(discord.ui, "LayoutView"):
    raise SystemExit(
        "Seu discord.py é antigo e não tem os Components V2\n"
        "Atualize com:  py -m pip install -U discord.py"
    )

# ---------------------------------------------------------------------------
# Configurações personalizáveis
# ---------------------------------------------------------------------------
POLICHINELOS_MAXIMOS = 500
TEMPO_DE_FECHAMENTO = 5
CLOSE_DELAY = 5
BAR_SIZE = 20
TZ = ZoneInfo("America/Sao_Paulo")

pasta = Path(__file__).parent
DATA_FILE = pasta / "data.json"

red = discord.Colour(0xC0392B)
orange = discord.Colour(0xE67E22)
gold = discord.Colour(0xF1C40F)
green = discord.Colour(0x2ECC71)
blue = discord.Colour(0x5865F2)
grey = discord.Colour(0x95A5A6)

RODAPE = "-# Punições Oficiais • Exército Brasileiro"
RODAPE_CONTROLES = "-# Correção de polichinelos • Controles do aplicador"

# ---------------------------------------------------------------------------
# Dados
# ---------------------------------------------------------------------------
db = {"guilds": {}, "punishments": {}}
if DATA_FILE.exists():
    db = json.loads(DATA_FILE.read_text(encoding="utf-8"))


def save():
    DATA_FILE.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8")


def cfg(gid: int) -> dict:
    return db["guilds"].setdefault(str(gid), {})


def staff(u: discord.Member, g: discord.Guild) -> bool:
    if u.guild_permissions.administrator:
        return True
    rid = cfg(g.id).get("staff_role")
    return bool(rid) and any(r.id == rid for r in u.roles)


def get_token() -> str:
    tk = os.environ.get("DISCORD_TOKEN")
    arq = pasta / "token.txt"
    if not tk and arq.exists():
        tk = arq.read_text(encoding="utf-8").strip()
    if not tk:
        raise SystemExit(
            "Token não encontrado.\n"
            "Crie um arquivo token.txt (só com o token dentro) na mesma pasta do index.py "
            "ou defina a variável DISCORD_TOKEN."
        )
    return tk


# ---------------------------------------------------------------------------
# Números por extenso
# ---------------------------------------------------------------------------
unid = ["zero", "um", "dois", "três", "quatro", "cinco", "seis", "sete", "oito",
        "nove", "dez", "onze", "doze", "treze", "catorze", "quinze", "dezesseis",
        "dezessete", "dezoito", "dezenove"]
dez = ["", "", "vinte", "trinta", "quarenta", "cinquenta", "sessenta", "setenta",
       "oitenta", "noventa"]
cent = ["", "cento", "duzentos", "trezentos", "quatrocentos", "quinhentos",
        "seiscentos", "setecentos", "oitocentos", "novecentos"]


def ext(n: int) -> str:
    if n < 20:
        return unid[n]
    if n < 100:
        d, u = divmod(n, 10)
        return dez[d] + (f" e {unid[u]}" if u else "")
    if n == 100:
        return "cem"
    c, r = divmod(n, 100)
    return cent[c] + (f" e {ext(r)}" if r else "")


def formas(n: int) -> list:
    b = ext(n).upper()
    f = [b]
    if "CATORZE" in b:
        f.append(b.replace("CATORZE", "QUATORZE"))
    return [x + "!" for x in f]


def esp(n: int) -> str:
    return " ou ".join(formas(n))


def certo(txt: str, n: int) -> bool:
    r = unicodedata.normalize("NFC", txt.strip()).upper()
    return r in {unicodedata.normalize("NFC", x) for x in formas(n)}


# ---------------------------------------------------------------------------
# Leitura de relatório 
# ---------------------------------------------------------------------------
rot = {
    "responsavel": r"Respons[aá]vel",
    "permissao": r"Permiss[aã]o",
    "punido": r"Punido\(a\)",
    "justificativa": r"Justificativa",
    "quantidade": r"Quantidade(?: de polichinelos)?",
    "data": r"Data e hora",
}
men_re = re.compile(r"<@!?(\d+)>")
cab_re = re.compile(r"\s*relat[oó]rio de puni[cç][aã]o", re.I)


def ler_rel(txt: str) -> dict:
    t = txt.replace("**", "")
    fim = "|".join(rot.values())

    def pega(k: str):
        m = re.search(
            rf"(?:^|\n)[ \t]*{rot[k]}[ \t]*:[ \t]*(.*?)(?=\n[ \t]*(?:{fim})[ \t]*:|\Z)",
            t, re.I | re.S)
        return m.group(1).strip() if m else None

    def idm(v):
        m = men_re.search(v or "")
        return int(m.group(1)) if m else None

    q = re.search(r"\d+", pega("quantidade") or "")
    return {
        "resp": idm(pega("responsavel")),
        "perm": idm(pega("permissao")),
        "punido": idm(pega("punido")),
        "just": pega("justificativa"),
        "qtd": int(q.group()) if q else None,
    }


# ---------------------------------------------------------------------------
# Formatação
# ---------------------------------------------------------------------------
def hoje() -> datetime:
    return datetime.now(TZ)


def fdata(dt: datetime) -> str:
    return dt.astimezone(TZ).strftime("%d/%m/%Y | %H:%M")


def ts(dt: datetime, e: str = "F") -> str:
    return f"<t:{int(dt.timestamp())}:{e}>"


def fdur(d: timedelta) -> str:
    tot = max(int(d.total_seconds()), 0)
    h, r = divmod(tot, 3600)
    mi, s = divmod(r, 60)
    ps = []
    if h:
        ps.append(f"{h}h")
    if mi or h:
        ps.append(f"{mi}min")
    ps.append(f"{s}s")
    return " ".join(ps)


def cita(t: str) -> str:
    ls = (t or "—").splitlines() or ["—"]
    return "\n".join(f"> {l}" if l else ">" for l in ls)


def barra(a: int, t: int, tam: int = BAR_SIZE) -> str:
    n = round(a / t * tam) if t else 0
    return "▰" * n + "▱" * (tam - n)


def cor_de(pct: int, feito: bool) -> discord.Colour:
    if feito:
        return green
    if pct < 34:
        return red
    if pct < 67:
        return green
    return gold


def etapa(pct: int, feito: bool) -> str:
    if feito:
        return "Concluída"
    if pct == 0:
        return "Aguardando início"
    if pct < 34:
        return "Início"
    if pct < 67:
        return "Em andamento"
    return "Reta final"


def box(titulo: str, corpo: str, cor: discord.Colour, rodape: str = RODAPE) -> discord.ui.LayoutView:
    v = discord.ui.LayoutView(timeout=None)
    c = discord.ui.Container(accent_color=cor)
    c.add_item(discord.ui.TextDisplay(f"## {titulo}"))
    c.add_item(discord.ui.Separator())
    c.add_item(discord.ui.TextDisplay(corpo))
    if rodape:
        c.add_item(discord.ui.Separator(visible=False))
        c.add_item(discord.ui.TextDisplay(rodape))
    v.add_item(c)
    return v


def ok(corpo: str, titulo: str = "Operação concluída") -> discord.ui.LayoutView:
    return box(titulo, corpo, green)


def bad(corpo: str, titulo: str = "Não foi possível concluir") -> discord.ui.LayoutView:
    return box(titulo, corpo, red)


def info(corpo: str, titulo: str = "Informação") -> discord.ui.LayoutView:
    return box(titulo, corpo, blue)


def rel_pun(resp, perm, quem, just, dt: datetime, qtd: int, ch) -> discord.ui.LayoutView:
    v = discord.ui.LayoutView(timeout=None)
    c = discord.ui.Container(accent_color=red)
    c.add_item(discord.ui.TextDisplay(
        "## Relatório de Punição\n"
        "-# Registro oficial de aplicação de punição"
    ))
    c.add_item(discord.ui.Separator())
    c.add_item(discord.ui.TextDisplay(
        "### Envolvidos\n"
        f"**Responsável:** {resp}\n"
        f"**Permissão:** {perm}\n"
        f"**Punido(a):** {quem}"
    ))
    c.add_item(discord.ui.Separator())
    c.add_item(discord.ui.TextDisplay(
        "### Detalhes da punição\n"
        f"**Quantidade de polichinelos:** {qtd}\n"
        f"**Canal da correção:** {ch}\n"
        f"**Data e hora:** {fdata(dt)} ({ts(dt, 'R')})"
    ))
    c.add_item(discord.ui.Separator())
    c.add_item(discord.ui.TextDisplay(f"### Justificativa\n{cita(just)}"))
    c.add_item(discord.ui.Separator(visible=False))
    c.add_item(discord.ui.TextDisplay(RODAPE))
    v.add_item(c)
    return v


def rel_fim(ap, quem, qtd: int, motivo: str, dt: datetime, dur: str, erros: int) -> discord.ui.LayoutView:
    v = discord.ui.LayoutView(timeout=None)
    c = discord.ui.Container(accent_color=green)
    c.add_item(discord.ui.TextDisplay(
        "## Relatório de Finalização de Punição\n"
        "-# Registro oficial de cumprimento de punição"
    ))
    c.add_item(discord.ui.Separator())
    c.add_item(discord.ui.TextDisplay(
        "### Envolvidos\n"
        f"**Aplicador:** {ap}\n"
        f"**Punido(a):** {quem}"
    ))
    c.add_item(discord.ui.Separator())
    c.add_item(discord.ui.TextDisplay(
        "### Desempenho\n"
        f"**Quantidade de polichinelos:** {qtd}\n"
        f"**Tempo total:** {dur}\n"
        f"**Erros cometidos:** {erros}\n"
        f"**Data e hora:** {fdata(dt)} ({ts(dt, 'R')})"
    ))
    c.add_item(discord.ui.Separator())
    c.add_item(discord.ui.TextDisplay(f"### Motivo da punição\n{cita(motivo)}"))
    c.add_item(discord.ui.Separator(visible=False))
    c.add_item(discord.ui.TextDisplay(RODAPE))
    v.add_item(c)
    return v


# ---------------------------------------------------------------------------
# Painel do ticket
# ---------------------------------------------------------------------------
class Painel(discord.ui.LayoutView):
    def __init__(self, p: dict):
        super().__init__(timeout=None)
        tot, at = p["total"], p["current"]
        fim = p["phase"] in ("finishing", "finished")
        feitos = tot if fim else at
        pct = 100 if fim else int(at / tot * 100)
        falta = tot - feitos
        erros = p.get("errors", 0)
        uid = p["user_id"]
        criado = datetime.fromisoformat(p["created_at"])
        perm = f"<@{p['permission_id']}>" if p.get("permission_id") else "—"

        if fim:
            ab = (
                "## Punição concluída\n"
                f"<@{uid}> cumpriu os **{tot} polichinelos**.\n"
                "-# O acesso a este canal será encerrado em instantes."
            )
        else:
            ab = (
                "## Punição em andamento\n"
                f"<@{uid}> tem **{tot} polichinelos** para cumprir.\n"
                "-# Leia as instruções abaixo e comece quando estiver pronto."
            )

        c1 = discord.ui.Container(accent_color=cor_de(pct, fim))
        if p.get("avatar_url"):
            c1.add_item(discord.ui.Section(
                discord.ui.TextDisplay(ab),
                accessory=discord.ui.Thumbnail(p["avatar_url"]),
            ))
        else:
            c1.add_item(discord.ui.TextDisplay(ab))
        c1.add_item(discord.ui.Separator())
        c1.add_item(discord.ui.TextDisplay(
            f"`{barra(feitos, tot)}` **{pct}%**\n"
            f"**{feitos}** de **{tot}** cumpridos • **{falta}** restantes\n"
            f"-# {etapa(pct, fim)} • {erros} {'erro' if erros == 1 else 'erros'}"
        ))
        self.add_item(c1)

        c2 = discord.ui.Container()
        c2.add_item(discord.ui.TextDisplay(
            f"**Aplicador:** <@{p['applicator_id']}>\n"
            f"**Permissão:** {perm}\n"
            f"**Abertura:** {fdata(criado)} ({ts(criado, 'R')})"
        ))
        c2.add_item(discord.ui.Separator())
        c2.add_item(discord.ui.TextDisplay(f"**Justificativa**\n{cita(p['reason'])}"))
        if fim:
            c2.add_item(discord.ui.Separator(visible=False))
            c2.add_item(discord.ui.TextDisplay(RODAPE))
        self.add_item(c2)

        if not fim:
            c3 = discord.ui.Container()
            c3.add_item(discord.ui.TextDisplay(
                "### Como funciona\n"
                "Envie **um número por mensagem**, em ordem, por extenso, "
                "com acento e exclamação:\n"
                "`UM!`  `DOIS!`  `TRÊS!`  `QUATRO!`\n\n"
                f"Se errar, o canal fecha por **{TEMPO_DE_FECHAMENTO} segundos** e você retoma "
                "do último número certo.\n\n"
                f"**Próximo número:** `{esp(at + 1)}`"
            ))
            c3.add_item(discord.ui.Separator(visible=False))
            c3.add_item(discord.ui.TextDisplay(RODAPE))
            self.add_item(c3)


tarefas: dict = {}


def cancela(cid: int):
    t = tarefas.pop(cid, None)
    if t:
        t.cancel()


async def atualiza(ch: discord.TextChannel, p: dict):
    if not p.get("panel_message_id"):
        return
    with contextlib.suppress(discord.HTTPException):
        await ch.get_partial_message(p["panel_message_id"]).edit(view=Painel(p))


def agenda(ch: discord.TextChannel, p: dict):
    if ch.id in tarefas:
        return

    async def job():
        await asyncio.sleep(1.5)
        tarefas.pop(ch.id, None)
        await atualiza(ch, p)

    tarefas[ch.id] = asyncio.create_task(job())


# ---------------------------------------------------------------------------
# Bot
# ---------------------------------------------------------------------------
its = discord.Intents.default()
its.message_content = True


class Pol(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=its)

    async def setup_hook(self):
        self.add_view(Fim(None))
        await self.tree.sync()


bot = Pol()
travados: set = set()
retom = {"ok": False}


def slug(nome: str) -> str:
    nome = re.sub(r"[^a-z0-9_-]", "", nome.lower())
    return nome[:20] or "usuario"


async def envio(ch: discord.TextChannel, u: discord.Member, liberar: bool):
    o = ch.overwrites_for(u)
    o.send_messages = liberar
    await ch.set_permissions(u, overwrite=o)


@bot.event
async def on_ready():
    if retom["ok"]:
        return
    retom["ok"] = True
    for cid, p in list(db["punishments"].items()):
        if p.get("phase") == "finishing":
            ch = bot.get_channel(int(cid))
            if ch:
                asyncio.create_task(controles(ch, p))


async def abrir(g, rel, u: discord.Member, qtd: int, ap: int, perm, just: str,
                dt: datetime, log: str) -> discord.TextChannel:
    c = cfg(g.id)
    ow = {
        g.default_role: discord.PermissionOverwrite(view_channel=False),
        u: discord.PermissionOverwrite(view_channel=True, send_messages=True,
                                       read_message_history=True),
        g.me: discord.PermissionOverwrite(view_channel=True, send_messages=True,
                                          read_message_history=True,
                                          manage_channels=True, manage_permissions=True),
    }
    cargo = g.get_role(c.get("staff_role") or 0)
    if cargo:
        ow[cargo] = discord.PermissionOverwrite(
            view_channel=True, read_message_history=True, send_messages=False)

    ch = await g.create_text_channel(
        name=f"punição-{slug(u.name)}",
        category=rel.category,
        overwrites=ow,
        topic=f"Correção de {u.display_name} • {qtd} polichinelos",
        reason=log,
    )
    p = {
        "guild_id": g.id, "channel_id": ch.id, "user_id": u.id,
        "phase": "counting", "current": 0, "total": qtd, "errors": 0,
        "applicator_id": ap, "permission_id": perm,
        "reason": just, "report_sent": False,
        "created_at": dt.isoformat(), "avatar_url": u.display_avatar.url,
        "panel_message_id": None,
    }
    db["punishments"][str(ch.id)] = p
    save()

    try:
        msg = await ch.send(view=Painel(p),
                            allowed_mentions=discord.AllowedMentions(users=[u]))
    except (discord.Forbidden, discord.HTTPException):
        db["punishments"].pop(str(ch.id), None)
        save()
        with contextlib.suppress(discord.HTTPException):
            await ch.delete(reason="Falha ao enviar o painel")
        raise
    p["panel_message_id"] = msg.id
    save()
    return ch


def emoji(g: discord.Guild):
    e = discord.utils.get(g.emojis, name="verified")
    if e:
        return e
    e = next((x for x in g.emojis if "verified" in x.name.lower()), None)
    return e or "✅"


async def manual(m: discord.Message):
    if not cab_re.match(m.content.replace("**", "")):
        return
    g = m.guild
    d = ler_rel(m.content)
    err = None
    u = None

    if not d["punido"]:
        err = "Não encontrei a menção do **Punido(a)** no relatório."
    elif d["qtd"] is None:
        err = ("Faltou a linha **Quantidade de polichinelos: N** no relatório. "
               "O bot precisa dela para criar a correção.")
    elif not 1 <= d["qtd"] <= POLICHINELOS_MAXIMOS:
        err = f"A quantidade deve ficar entre **1** e **{POLICHINELOS_MAXIMOS}**."
    else:
        u = next((x for x in m.mentions if x.id == d["punido"]), None)
        if not isinstance(u, discord.Member):
            try:
                u = await g.fetch_member(d["punido"])
            except discord.HTTPException:
                err = "Não encontrei o punido neste servidor."
        if u and u.bot:
            err = "Não é possível punir um bot."

    if not err:
        try:
            await abrir(
                g, m.channel, u, d["qtd"],
                ap=d["resp"] or m.author.id,
                perm=d["perm"],
                just=(d["just"] or "—")[:800],
                dt=hoje(),
                log=f"Relatório enviado por {m.author}",
            )
        except (discord.Forbidden, discord.HTTPException):
            err = ("Não consegui criar o canal da correção. Confira as permissões do bot "
                   "(**Gerenciar Canais** e **Gerenciar Permissões**).")

    with contextlib.suppress(discord.HTTPException):
        if err:
            await m.add_reaction("❌")
            await m.reply(
                view=bad(err, "Relatório não processado"),
                delete_after=20, mention_author=False)
        else:
            await m.add_reaction(emoji(g))


@bot.event
async def on_message(m: discord.Message):
    if m.author.bot or not m.guild:
        return

    if m.channel.id == cfg(m.guild.id).get("punishment_channel"):
        await manual(m)
        return

    p = db["punishments"].get(str(m.channel.id))
    if not p or p["phase"] != "counting" or m.author.id != p["user_id"]:
        return
    if m.channel.id in travados:
        return

    n = p["current"] + 1
    if certo(m.content, n):
        p["current"] = n
        save()
        if n >= p["total"]:
            await acabar(m.channel, m.author, p)
        else:
            agenda(m.channel, p)
        return

    travados.add(m.channel.id)
    cancela(m.channel.id)
    p["errors"] = p.get("errors", 0) + 1
    save()
    sp = discord.AllowedMentions.none()
    try:
        await envio(m.channel, m.author, False)
        await m.channel.send(
            view=box(
                "Resposta incorreta",
                f"{m.author.mention} errou a sequência.\n"
                f"**Esperado:** {esp(n)}\n"
                f"**Erros acumulados:** {p['errors']}\n\n"
                f"O canal permanece fechado por **{TEMPO_DE_FECHAMENTO} segundos**.",
                red),
            allowed_mentions=sp)
        await atualiza(m.channel, p)
        await asyncio.sleep(TEMPO_DE_FECHAMENTO)
        await envio(m.channel, m.author, True)
    finally:
        travados.discard(m.channel.id)

    if p["current"] == 0:
        txt = f"O canal foi reaberto.\nRecomece pelo **{esp(1)}**"
    else:
        txt = (
            "O canal foi reaberto.\n"
            f"**Último número correto:** {esp(p['current'])} "
            f"({p['current']} de {p['total']})\n"
            f"**Continue com:** {esp(p['current'] + 1)}"
        )
    await m.channel.send(view=box("Canal reaberto", txt, green), allowed_mentions=sp)


# ---------------------------------------------------------------------------
# Fim da punição
# ---------------------------------------------------------------------------
async def acabar(ch: discord.TextChannel, u: discord.Member, p: dict):
    fim = hoje()
    p["phase"] = "finishing"
    p["finished_at"] = fim.isoformat()
    save()
    cancela(ch.id)

    with contextlib.suppress(discord.HTTPException):
        await envio(ch, u, False)
    await atualiza(ch, p)

    ini = datetime.fromisoformat(p["created_at"])
    await ch.send(
        view=box(
            "Correção concluída",
            f"<@{p['user_id']}> terminou os **{p['total']} polichinelos**, "
            f"do {esp(1)} até o {esp(p['total'])}\n\n"
            f"**Tempo total:** {fdur(fim - ini)}\n"
            f"**Erros cometidos:** {p.get('errors', 0)}\n\n"
            f"O acesso ao canal será encerrado em **10 segundos**.",
            green),
        allowed_mentions=discord.AllowedMentions(users=True))

    await asyncio.sleep(10)
    await controles(ch, p, u)


async def controles(ch: discord.TextChannel, p: dict, mem: discord.Member = None):
    uid = p["user_id"]
    if mem is None:
        mem = ch.guild.get_member(uid)
    if mem is None:
        with contextlib.suppress(discord.HTTPException):
            mem = await ch.guild.fetch_member(uid)
    if mem is not None:
        with contextlib.suppress(discord.HTTPException):
            await ch.set_permissions(mem, overwrite=None, reason="Correção finalizada")
    p["phase"] = "finished"
    save()

    await ch.send(view=Fim(p), allowed_mentions=discord.AllowedMentions(users=True))


def pode(i: discord.Interaction, p: dict) -> bool:
    return i.user.id == p["applicator_id"] or staff(i.user, i.guild)


async def cb_rel(i: discord.Interaction):
    p = db["punishments"].get(str(i.channel.id))
    if not p:
        return await i.response.send_message(
            view=bad("Nenhuma punição ativa foi encontrada neste canal.", "Punição não encontrada"),
            ephemeral=True)
    if not pode(i, p):
        return await i.response.send_message(
            view=bad("Apenas o aplicador ou a equipe podem usar este botão.", "Acesso negado"),
            ephemeral=True)
    if p.get("report_sent"):
        return await i.response.send_message(
            view=info("O relatório de finalização desta punição já foi enviado.", "Relatório já enviado"),
            ephemeral=True)

    cid = cfg(i.guild.id).get("report_channel")
    dest = i.guild.get_channel(cid) if cid else None
    if not dest:
        return await i.response.send_message(
            view=bad(
                "O canal de relatórios de finalização ainda não foi definido.\n"
                "Use `/relatorio_finalizacao` para configurá-lo.",
                "Canal não configurado"),
            ephemeral=True)

    p["report_sent"] = True
    await i.response.defer()

    ag = hoje()
    ini = datetime.fromisoformat(p["created_at"])
    fim = datetime.fromisoformat(p["finished_at"]) if p.get("finished_at") else ag

    try:
        await dest.send(
            view=rel_fim(
                ap=f"<@{p['applicator_id']}>",
                quem=f"<@{p['user_id']}>",
                qtd=p["total"],
                motivo=p["reason"] or "—",
                dt=ag,
                dur=fdur(fim - ini),
                erros=p.get("errors", 0),
            ),
            allowed_mentions=discord.AllowedMentions.none(),
        )
    except (discord.Forbidden, discord.HTTPException) as e:
        p["report_sent"] = False
        return await i.followup.send(
            view=bad(
                f"Não consegui enviar o relatório em {dest.mention}.\n`{e}`",
                "Falha no envio"),
            ephemeral=True)

    save()
    await i.edit_original_response(view=Fim(p))
    await i.followup.send(
        view=ok(f"O relatório de finalização foi enviado em {dest.mention}.",
                "Relatório enviado"),
        ephemeral=True)


async def cb_fecha(i: discord.Interaction):
    p = db["punishments"].get(str(i.channel.id))
    if not p:
        return await i.response.send_message(
            view=bad("Nenhuma punição ativa foi encontrada neste canal.", "Punição não encontrada"),
            ephemeral=True)
    if not pode(i, p):
        return await i.response.send_message(
            view=bad("Apenas o aplicador ou a equipe podem usar este botão.", "Acesso negado"),
            ephemeral=True)

    await i.response.send_message(
        view=box(
            "Encerrando canal",
            f"Este canal será excluído em **{CLOSE_DELAY} segundos**.\n"
            f"**Solicitado por:** {i.user.mention}",
            grey),
        allowed_mentions=discord.AllowedMentions.none())
    await asyncio.sleep(CLOSE_DELAY)
    db["punishments"].pop(str(i.channel.id), None)
    save()
    await i.channel.delete(reason=f"Fechado por {i.user}")


class Fim(discord.ui.LayoutView):
    def __init__(self, p: dict = None):
        super().__init__(timeout=None)
        env = bool(p and p.get("report_sent"))

        c = discord.ui.Container(accent_color=green if env else blue)

        if p:
            ini = datetime.fromisoformat(p["created_at"])
            fim = datetime.fromisoformat(p["finished_at"]) if p.get("finished_at") else hoje()
            c.add_item(discord.ui.TextDisplay(
                "## Controles da punição\n"
                f"<@{p['applicator_id']}>, a correção de <@{p['user_id']}> terminou "
                "e o acesso dele(a) a este canal foi encerrado."
            ))
            c.add_item(discord.ui.Separator())
            c.add_item(discord.ui.TextDisplay(
                "### Resumo da correção\n"
                f"**Quantidade cumprida:** {p['total']} polichinelos\n"
                f"**Tempo total:** {fdur(fim - ini)}\n"
                f"**Erros cometidos:** {p.get('errors', 0)}\n"
                f"**Relatório de finalização:** {'Enviado' if env else 'Pendente'}"
            ))
        else:
            c.add_item(discord.ui.TextDisplay("## Controles da punição"))

        c.add_item(discord.ui.Separator())
        c.add_item(discord.ui.TextDisplay(
            "### Próximos passos\n"
            "**1.** Envie o relatório de finalização.\n"
            "**2.** Feche o canal.\n\n"
            "Apenas o aplicador e a equipe podem usar os botões."
        ))

        b1 = discord.ui.Button(
            label="Relatório enviado" if env else "Enviar relatório de finalização",
            style=discord.ButtonStyle.secondary if env else discord.ButtonStyle.success,
            custom_id="pol:report", disabled=env)
        b1.callback = cb_rel

        b2 = discord.ui.Button(
            label="Fechar canal", style=discord.ButtonStyle.danger, custom_id="pol:close")
        b2.callback = cb_fecha

        row = discord.ui.ActionRow()
        row.add_item(b1)
        row.add_item(b2)
        c.add_item(row)

        c.add_item(discord.ui.Separator(visible=False))
        c.add_item(discord.ui.TextDisplay(RODAPE_CONTROLES))
        self.add_item(c)


# ---------------------------------------------------------------------------
# Comandos
# ---------------------------------------------------------------------------
def so_staff():
    async def check(i: discord.Interaction) -> bool:
        if i.guild and staff(i.user, i.guild):
            return True
        raise app_commands.CheckFailure("sem permissão")
    return app_commands.check(check)


@bot.tree.command(name="equipe",
                  description="Define o cargo da equipe (vê os tickets, usa os botões finais e aplica punições)")
@app_commands.describe(cargo="Cargo da equipe")
@app_commands.default_permissions(administrator=True)
@app_commands.checks.has_permissions(administrator=True)
@app_commands.guild_only()
async def equipe(i: discord.Interaction, cargo: discord.Role):
    cfg(i.guild.id)["staff_role"] = cargo.id
    save()
    await i.response.send_message(
        view=box(
            "Cargo da equipe definido",
            f"**Cargo:** {cargo.mention}\n\n"
            "### Permissões concedidas\n"
            "• Visualizar os tickets criados a partir de agora\n"
            "• Usar os botões finais (relatório e fechar canal)\n"
            "• Aplicar punições com `/punir`",
            green),
        ephemeral=True, allowed_mentions=discord.AllowedMentions.none())


@bot.tree.command(name="relatorio_punicao",
                  description="Define o canal dos relatórios de punição (enviados pelo bot ou por pessoas)")
@app_commands.describe(canal="Canal dos relatórios de punição")
@app_commands.default_permissions(administrator=True)
@app_commands.checks.has_permissions(administrator=True)
@app_commands.guild_only()
async def rpun(i: discord.Interaction, canal: discord.TextChannel):
    cfg(i.guild.id)["punishment_channel"] = canal.id
    save()
    await i.response.send_message(
        view=box(
            "Canal de relatórios de punição definido",
            f"**Canal:** {canal.mention}\n"
            "Os canais de correção serão criados na mesma categoria.\n\n"
            "### Como funciona\n"
            "• Com `/punir`, o bot envia o relatório e cria a correção.\n"
            "• Se uma pessoa escrever o relatório, o bot reage com :verified: e cria a correção.\n"
            "• Nos relatórios manuais, inclua a linha `Quantidade de polichinelos: N`.",
            green),
        ephemeral=True, allowed_mentions=discord.AllowedMentions.none())


@bot.tree.command(name="relatorio_finalizacao",
                  description="Define o canal onde os relatórios de finalização serão enviados")
@app_commands.describe(canal="Canal dos relatórios de finalização")
@app_commands.default_permissions(administrator=True)
@app_commands.checks.has_permissions(administrator=True)
@app_commands.guild_only()
async def rfim(i: discord.Interaction, canal: discord.TextChannel):
    cfg(i.guild.id)["report_channel"] = canal.id
    save()
    await i.response.send_message(
        view=box(
            "Canal de relatórios de finalização definido",
            f"**Canal:** {canal.mention}\n"
            "Os relatórios de finalização serão enviados neste canal quando o aplicador "
            "usar o botão de relatório.",
            green),
        ephemeral=True, allowed_mentions=discord.AllowedMentions.none())


@bot.tree.command(name="punir",
                  description="Aplica a punição: envia o relatório e cria o canal da correção")
@app_commands.describe(
    punido="Quem vai cumprir a correção",
    quantidade="Quantidade de polichinelos",
    permissao="Quem deu a permissão para a punição",
    justificativa="Motivo da punição",
)
@app_commands.guild_only()
@so_staff()
async def punir(
    i: discord.Interaction,
    punido: discord.Member,
    quantidade: app_commands.Range[int, 1, POLICHINELOS_MAXIMOS],
    permissao: discord.Member,
    justificativa: app_commands.Range[str, 1, 800],
):
    g = i.guild
    rel = g.get_channel(cfg(g.id).get("punishment_channel") or 0)
    if not rel:
        return await i.response.send_message(
            view=bad(
                "Defina primeiro o canal do relatório de punição com `/relatorio_punicao`.",
                "Canal não configurado"),
            ephemeral=True)
    if punido.bot:
        return await i.response.send_message(
            view=bad("Não é possível punir um bot.", "Alvo inválido"),
            ephemeral=True)

    await i.response.defer(ephemeral=True)
    ag = hoje()
    ch = None
    try:
        ch = await abrir(
            g, rel, punido, quantidade,
            ap=i.user.id, perm=permissao.id,
            just=justificativa, dt=ag,
            log=f"Punição aplicada por {i.user}",
        )
        await rel.send(
            view=rel_pun(
                resp=i.user.mention,
                perm=permissao.mention,
                quem=punido.mention,
                just=justificativa,
                dt=ag,
                qtd=quantidade,
                ch=ch.mention,
            ),
            allowed_mentions=discord.AllowedMentions.none(),
        )
    except (discord.Forbidden, discord.HTTPException) as e:
        if ch:
            db["punishments"].pop(str(ch.id), None)
            save()
            with contextlib.suppress(discord.HTTPException):
                await ch.delete(reason="Falha ao enviar o relatório")
        return await i.followup.send(
            view=bad(
                f"Não consegui concluir a punição.\n`{e}`\n\n"
                "Confira as permissões do bot: **Gerenciar Canais**, **Gerenciar Permissões** "
                "e enviar mensagens no canal do relatório.",
                "Falha ao aplicar punição"),
            ephemeral=True)

    await i.followup.send(
        view=box(
            "Punição aplicada",
            f"**Punido(a):** {punido.mention}\n"
            f"**Quantidade:** {quantidade} polichinelos\n"
            f"**Canal da correção:** {ch.mention}\n"
            f"**Relatório enviado em:** {rel.mention}",
            green),
        ephemeral=True, allowed_mentions=discord.AllowedMentions.none())


@bot.tree.error
async def erro_cmd(i: discord.Interaction, e: app_commands.AppCommandError):
    if isinstance(e, app_commands.CheckFailure):
        v = bad("Você não tem permissão para usar este comando.", "Acesso negado")
        if i.response.is_done():
            await i.followup.send(view=v, ephemeral=True)
        else:
            await i.response.send_message(view=v, ephemeral=True)
    else:
        raise e


bot.run(get_token())
