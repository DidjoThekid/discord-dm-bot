"""
Bot Discord — envoi et réception de messages privés (DM)
"""

import os
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


if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError(
            "DISCORD_TOKEN manquant. Crée un fichier .env avec DISCORD_TOKEN=ton_token"
        )
    bot.run(TOKEN)
