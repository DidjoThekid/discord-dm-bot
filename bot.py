"""
Bot Discord — envoi et réception de messages privés (DM)
"""

import os
import asyncio
import logging

import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
DM_LOG_CHANNEL_ID = os.getenv("DM_LOG_CHANNEL_ID")
DM_LOG_CHANNEL_ID = int(DM_LOG_CHANNEL_ID) if DM_LOG_CHANNEL_ID else None

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("dm-bot")

intents = discord.Intents.default()
intents.message_content = True
intents.dm_messages = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    log.info(f"Connecté en tant que {bot.user} (ID: {bot.user.id})")
    log.info("Le bot est prêt à envoyer/recevoir des DM.")


@bot.event
async def on_message(message: discord.Message):
    if message.author == bot.user:
        return

    if isinstance(message.channel, discord.DMChannel):
        log.info(f"[DM reçu] {message.author} ({message.author.id}) : {message.content}")

        if DM_LOG_CHANNEL_ID:
            channel = bot.get_channel(DM_LOG_CHANNEL_ID)
            if channel:
                await channel.send(
                    f"📩 **DM de {message.author}** (`{message.author.id}`) :\n{message.content}"
                )

        await message.channel.send(
            f"J'ai bien reçu ton message : « {message.content} »"
        )

    await bot.process_commands(message)


@bot.command(name="dm")
@commands.has_permissions(administrator=True)
async def send_dm(ctx: commands.Context, user_id: int, *, message: str):
    """Envoie un DM à un utilisateur via son ID Discord."""
    try:
        user = await bot.fetch_user(user_id)
        await user.send(message)
        await ctx.send(f"✅ Message envoyé à {user} (`{user_id}`).")
        log.info(f"[DM envoyé] à {user} ({user_id}) : {message}")
    except discord.Forbidden:
        await ctx.send("❌ Impossible d'envoyer un DM à cet utilisateur (DM fermés ou bot bloqué).")
    except discord.NotFound:
        await ctx.send("❌ Utilisateur introuvable avec cet ID.")
    except Exception as e:
        await ctx.send(f"❌ Erreur : {e}")
        log.exception("Erreur lors de l'envoi du DM")


@send_dm.error
async def send_dm_error(ctx: commands.Context, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Tu dois être administrateur pour utiliser cette commande.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Usage : `!dm <user_id> <message>`")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("❌ L'ID utilisateur doit être un nombre valide.")
    else:
        raise error


@bot.command(name="dmrole")
@commands.has_permissions(administrator=True)
@commands.guild_only()
async def send_dm_role(ctx: commands.Context, role: discord.Role, *, message: str):
    """Envoie un DM à tous les membres possédant un rôle donné."""
    members = [m for m in role.members if not m.bot]

    if not members:
        await ctx.send(f"⚠️ Aucun membre humain n'a le rôle **{role.name}**.")
        return

    status_msg = await ctx.send(
        f"📤 Envoi du message à **{len(members)}** membre(s) ayant le rôle **{role.name}**..."
    )

    sent, failed = 0, 0
    for member in members:
        try:
            await member.send(message)
            sent += 1
            log.info(f"[DM envoyé - rôle {role.name}] à {member} ({member.id})")
        except discord.Forbidden:
            failed += 1
            log.warning(f"[DM échoué - rôle {role.name}] à {member} ({member.id}) : DM fermés")
        except Exception as e:
            failed += 1
            log.exception(f"[DM échoué - rôle {role.name}] à {member} ({member.id})")

        await asyncio.sleep(1)

    await status_msg.edit(
        content=(
            f"✅ Terminé — message envoyé à **{sent}/{len(members)}** membre(s) "
            f"du rôle **{role.name}**"
            + (f" ({failed} échec(s), probablement des DM fermés)." if failed else ".")
        )
    )


@send_dm_role.error
async def send_dm_role_error(ctx: commands.Context, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Tu dois être administrateur pour utiliser cette commande.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Usage : `!dmrole <@rôle ou ID_du_rôle> <message>`")
    elif isinstance(error, commands.RoleNotFound):
        await ctx.send("❌ Rôle introuvable. Mentionne le rôle (@rôle) ou donne son ID.")
    elif isinstance(error, commands.NoPrivateMessage):
        await ctx.send("❌ Cette commande doit être utilisée dans un serveur, pas en DM.")
    else:
        raise error


@bot.command(name="send")
@commands.has_permissions(administrator=True)
@commands.guild_only()
async def send_to_channel(ctx: commands.Context, channel: discord.TextChannel, *, message: str):
    """Envoie un message dans un salon donné."""
    try:
        await channel.send(message)
        await ctx.send(f"✅ Message envoyé dans {channel.mention}.")
        log.info(f"[Message envoyé] dans #{channel.name} : {message}")
    except discord.Forbidden:
        await ctx.send("❌ Le bot n'a pas la permission d'écrire dans ce salon.")
    except Exception as e:
        await ctx.send(f"❌ Erreur : {e}")
        log.exception("Erreur lors de l'envoi dans le salon")


@send_to_channel.error
async def send_to_channel_error(ctx: commands.Context, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Tu dois être administrateur pour utiliser cette commande.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Usage : `!send <#salon> <message>`")
    elif isinstance(error, commands.ChannelNotFound):
        await ctx.send("❌ Salon introuvable. Mentionne le salon (#salon) ou donne son ID.")
    elif isinstance(error, commands.NoPrivateMessage):
        await ctx.send("❌ Cette commande doit être utilisée dans un serveur, pas en DM.")
    else:
        raise error


@bot.command(name="post")
@commands.has_permissions(administrator=True)
@commands.guild_only()
async def create_post(
    ctx: commands.Context,
    forum: discord.ForumChannel,
    titre: str,
    *,
    message: str,
):
    """Crée un nouveau post dans un salon de type Forum. Le titre doit être entre guillemets s'il contient des espaces."""
    try:
        result = await forum.create_thread(name=titre, content=message)
        thread = result.thread if hasattr(result, "thread") else result
        await ctx.send(f"✅ Post créé : {thread.mention}")
        log.info(f"[Post créé] dans #{forum.name} : {titre}")
    except discord.Forbidden:
        await ctx.send("❌ Le bot n'a pas la permission de créer un post dans ce forum.")
    except Exception as e:
        await ctx.send(f"❌ Erreur : {e}")
        log.exception("Erreur lors de la création du post")


@create_post.error
async def create_post_error(ctx: commands.Context, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Tu dois être administrateur pour utiliser cette commande.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send('Usage : `!post <#forum> "Titre du post" <message>`')
    elif isinstance(error, commands.ChannelNotFound):
        await ctx.send("❌ Salon de forum introuvable. Mentionne-le (#forum) ou donne son ID.")
    elif isinstance(error, commands.NoPrivateMessage):
        await ctx.send("❌ Cette commande doit être utilisée dans un serveur, pas en DM.")
    else:
        raise error


@bot.command(name="lock")
@commands.has_permissions(administrator=True)
@commands.guild_only()
async def lock_post(ctx: commands.Context, thread: discord.Thread = None):
    """Verrouille un post (thread). Sans argument, verrouille le post dans lequel la commande est tapée."""
    thread = thread or (ctx.channel if isinstance(ctx.channel, discord.Thread) else None)

    if thread is None:
        await ctx.send(
            "❌ Aucun post ciblé. Utilise cette commande à l'intérieur d'un post, "
            "ou donne son ID/lien : `!lock <ID_du_post>`."
        )
        return

    try:
        await thread.edit(locked=True, archived=True)
        await ctx.send(f"🔒 Le post **{thread.name}** a été verrouillé.")
        log.info(f"[Post verrouillé] {thread.name} ({thread.id})")
    except discord.Forbidden:
        await ctx.send("❌ Le bot n'a pas la permission de verrouiller ce post.")
    except Exception as e:
        await ctx.send(f"❌ Erreur : {e}")
        log.exception("Erreur lors du verrouillage du post")


@lock_post.error
async def lock_post_error(ctx: commands.Context, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Tu dois être administrateur pour utiliser cette commande.")
    elif isinstance(error, commands.ChannelNotFound):
        await ctx.send("❌ Post introuvable. Donne son ID ou utilise la commande dans le post.")
    elif isinstance(error, commands.NoPrivateMessage):
        await ctx.send("❌ Cette commande doit être utilisée dans un serveur, pas en DM.")
    else:
        raise error


@bot.command(name="unlock")
@commands.has_permissions(administrator=True)
@commands.guild_only()
async def unlock_post(ctx: commands.Context, thread: discord.Thread = None):
    """Déverrouille un post (thread). Sans argument, déverrouille le post dans lequel la commande est tapée."""
    thread = thread or (ctx.channel if isinstance(ctx.channel, discord.Thread) else None)

    if thread is None:
        await ctx.send(
            "❌ Aucun post ciblé. Utilise cette commande à l'intérieur d'un post, "
            "ou donne son ID/lien : `!unlock <ID_du_post>`."
        )
        return

    try:
        await thread.edit(locked=False, archived=False)
        await ctx.send(f"🔓 Le post **{thread.name}** a été déverrouillé.")
        log.info(f"[Post déverrouillé] {thread.name} ({thread.id})")
    except discord.Forbidden:
        await ctx.send("❌ Le bot n'a pas la permission de déverrouiller ce post.")
    except Exception as e:
        await ctx.send(f"❌ Erreur : {e}")
        log.exception("Erreur lors du déverrouillage du post")


@unlock_post.error
async def unlock_post_error(ctx: commands.Context, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Tu dois être administrateur pour utiliser cette commande.")
    elif isinstance(error, commands.ChannelNotFound):
        await ctx.send("❌ Post introuvable. Donne son ID ou utilise la commande dans le post.")
    elif isinstance(error, commands.NoPrivateMessage):
        await ctx.send("❌ Cette commande doit être utilisée dans un serveur, pas en DM.")
    else:
        raise error


@bot.command(name="deletepost")
@commands.has_permissions(administrator=True)
@commands.guild_only()
async def delete_post(ctx: commands.Context, thread: discord.Thread = None):
    """Supprime définitivement un post (thread). Sans argument, supprime le post dans lequel la commande est tapée."""
    thread = thread or (ctx.channel if isinstance(ctx.channel, discord.Thread) else None)

    if thread is None:
        await ctx.send(
            "❌ Aucun post ciblé. Utilise cette commande à l'intérieur d'un post, "
            "ou donne son ID/lien : `!deletepost <ID_du_post>`."
        )
        return

    thread_name = thread.name
    was_current_channel = thread.id == ctx.channel.id

    try:
        if was_current_channel:
            await ctx.send(f"🗑️ Suppression du post **{thread_name}**...")

        await thread.delete()
        log.info(f"[Post supprimé] {thread_name} ({thread.id})")

        if not was_current_channel:
            await ctx.send(f"🗑️ Le post **{thread_name}** a été supprimé.")
    except discord.Forbidden:
        await ctx.send("❌ Le bot n'a pas la permission de supprimer ce post.")
    except Exception as e:
        await ctx.send(f"❌ Erreur : {e}")
        log.exception("Erreur lors de la suppression du post")


@delete_post.error
async def delete_post_error(ctx: commands.Context, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Tu dois être administrateur pour utiliser cette commande.")
    elif isinstance(error, commands.ChannelNotFound):
        await ctx.send("❌ Post introuvable. Donne son ID ou utilise la commande dans le post.")
    elif isinstance(error, commands.NoPrivateMessage):
        await ctx.send("❌ Cette commande doit être utilisée dans un serveur, pas en DM.")
    else:
        raise error


if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError(
            "DISCORD_TOKEN manquant. Crée un fichier .env avec DISCORD_TOKEN=ton_token"
        )
    bot.run(TOKEN)
