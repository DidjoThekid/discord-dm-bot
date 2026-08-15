"""
Bot Discord — envoi et réception de messages privés (DM)
==========================================================

Fonctionnalités :
- Le bot répond automatiquement aux DM qu'il reçoit (les log dans la console
  et peut renvoyer une réponse).
- La commande !dm permet à un admin d'envoyer un DM à un utilisateur via
  son ID Discord.
- La commande !dmrole permet à un admin d'envoyer un DM à TOUS les membres
  possédant un rôle donné (ex: !dmrole @Membres Salut à tous !).
- La commande !send permet d'envoyer un message dans un salon du serveur.
- La commande !post permet de créer un nouveau post dans un salon Forum.
- Les commandes !lock et !unlock permettent de verrouiller/déverrouiller
  un post.
- La commande !deletepost permet de supprimer définitivement un post.
- La commande !call ouvre un salon vocal privé avec un membre : musique
  d'attente quelques secondes, puis annonce vocale de prise en charge.
  Accessible à TOUT LE MONDE pour s'appeler soi-même (!call sans
  argument) ; cibler quelqu'un d'autre (!call @membre) reste réservé
  aux admins.
- Les commandes !hold et !unhold mettent un appel en attente (sourdine +
  message vocal) puis le reprennent.
- Les commandes !closecalls et !opencalls permettent de fermer/rouvrir
  le service d'appel. Fermé, !call joue un message vocal d'indisponibilité
  et exclut la personne du salon vocal.
- Tous les DM reçus sont affichés dans la console, et peuvent être relayés
  vers un salon serveur si tu configures DM_LOG_CHANNEL_ID.

Installation :
    pip install -U discord.py python-dotenv

Configuration :
    1. Crée un fichier .env (voir .env.example) avec ton token de bot.
    2. Active l'intent "Message Content" dans le portail développeur Discord
       (https://discord.com/developers/applications -> ton appli -> Bot ->
       Privileged Gateway Intents -> MESSAGE CONTENT INTENT).
    3. Invite le bot sur un serveur (voir README.md pour le lien d'invitation).

Lancement :
    python bot.py
"""

import os
import asyncio
import time
import logging

import discord
from discord.ext import commands
from dotenv import load_dotenv
from gtts import gTTS

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
# ID du salon (dans un serveur) où relayer une copie des DM reçus. Optionnel.
DM_LOG_CHANNEL_ID = os.getenv("DM_LOG_CHANNEL_ID")
DM_LOG_CHANNEL_ID = int(DM_LOG_CHANNEL_ID) if DM_LOG_CHANNEL_ID else None

# ID(s) des rôles "Team DTK" (ou équivalents) qui doivent voir/rejoindre les
# appels privés. Plusieurs rôles peuvent être autorisés, séparés par des
# virgules, ex: STAFF_ROLE_IDS=111111111111111111,222222222222222222
STAFF_ROLE_IDS_RAW = os.getenv("STAFF_ROLE_IDS") or os.getenv("STAFF_ROLE_ID")
STAFF_ROLE_IDS = (
    [int(rid.strip()) for rid in STAFF_ROLE_IDS_RAW.split(",") if rid.strip()]
    if STAFF_ROLE_IDS_RAW
    else []
)
# Gardé pour compatibilité avec le reste du code (premier rôle configuré, ou None)
STAFF_ROLE_ID = STAFF_ROLE_IDS[0] if STAFF_ROLE_IDS else None

# ID d'une catégorie où ranger les salons d'appel créés. Optionnel.
CALL_CATEGORY_ID = os.getenv("CALL_CATEGORY_ID")
CALL_CATEGORY_ID = int(CALL_CATEGORY_ID) if CALL_CATEGORY_ID else None

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("dm-bot")

# ---------------------------------------------------------------------------
# Intents — MESSAGE CONTENT et DM sont nécessaires pour lire le contenu des DM
# ---------------------------------------------------------------------------

intents = discord.Intents.default()
intents.message_content = True  # nécessaire pour lire le texte des messages
intents.dm_messages = True      # nécessaire pour recevoir les événements DM
intents.members = True          # nécessaire pour lister les membres d'un rôle (!dmrole)

bot = commands.Bot(command_prefix="!", intents=intents)


# ---------------------------------------------------------------------------
# Événements
# ---------------------------------------------------------------------------

@bot.event
async def on_ready():
    log.info(f"Connecté en tant que {bot.user} (ID: {bot.user.id})")
    log.info("Le bot est prêt à envoyer/recevoir des DM.")


@bot.event
async def on_message(message: discord.Message):
    # Ignore les messages du bot lui-même
    if message.author == bot.user:
        return

    # Si le message vient d'un DM (pas d'un serveur)
    if isinstance(message.channel, discord.DMChannel):
        log.info(f"[DM reçu] {message.author} ({message.author.id}) : {message.content}")

        # Relaye le DM dans un salon serveur si configuré
        if DM_LOG_CHANNEL_ID:
            channel = bot.get_channel(DM_LOG_CHANNEL_ID)
            if channel:
                await channel.send(
                    f"📩 **DM de {message.author}** (`{message.author.id}`) :\n{message.content}"
                )

        # Exemple de réponse automatique — personnalise selon tes besoins
        await message.channel.send(
            f"J'ai bien reçu ton message : « {message.content} »"
        )

    # IMPORTANT : nécessaire pour que les commandes (!dm, etc.) fonctionnent
    await bot.process_commands(message)


# ---------------------------------------------------------------------------
# Commande pour envoyer un DM à un utilisateur depuis un serveur
# Usage : !dm <user_id> <message>
# ---------------------------------------------------------------------------

@bot.command(name="dm")
@commands.has_permissions(administrator=True)  # restreint aux admins — à ajuster
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


# ---------------------------------------------------------------------------
# Commande pour envoyer un DM à tous les membres ayant un rôle donné
# Usage : !dmrole <@role ou ID_du_rôle> <message>
# ---------------------------------------------------------------------------

@bot.command(name="dmrole")
@commands.has_permissions(administrator=True)  # restreint aux admins — à ajuster
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

        # Petite pause pour éviter de se faire limiter par Discord (rate limit)
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


# ---------------------------------------------------------------------------
# Commande pour envoyer un message dans un salon du serveur
# Usage : !send <#salon> <message>
# ---------------------------------------------------------------------------

@bot.command(name="send")
@commands.has_permissions(administrator=True)  # restreint aux admins — à ajuster
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


# ---------------------------------------------------------------------------
# Commande pour créer un post dans un salon de type "Forum"
# Usage : !post <#forum> "Titre du post" <message>
# ---------------------------------------------------------------------------

@bot.command(name="post")
@commands.has_permissions(administrator=True)  # restreint aux admins — à ajuster
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


# ---------------------------------------------------------------------------
# Commandes pour verrouiller / déverrouiller un post (thread)
# Usage : !lock [ID_ou_mention_du_post]   (sans argument = verrouille le post actuel)
#         !unlock [ID_ou_mention_du_post]
# ---------------------------------------------------------------------------

@bot.command(name="lock")
@commands.has_permissions(administrator=True)  # restreint aux admins — à ajuster
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
@commands.has_permissions(administrator=True)  # restreint aux admins — à ajuster
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


# ---------------------------------------------------------------------------
# Commande pour supprimer complètement un post (thread)
# Usage : !deletepost [ID_ou_mention_du_post]   (sans argument = supprime le post actuel)
# ---------------------------------------------------------------------------

@bot.command(name="deletepost")
@commands.has_permissions(administrator=True)  # restreint aux admins — à ajuster
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
        # Si la commande est tapée dans le post à supprimer, prévenir avant
        # de le supprimer, car la confirmation ne pourra pas être envoyée après.
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


# ---------------------------------------------------------------------------
# Appel privé — crée un salon vocal privé + message vocal d'accueil
# Usage : !call <@membre>
#
# IMPORTANT : un bot ne peut pas déclencher un vrai appel téléphonique/DM
# Discord (cette fonction est réservée au client Discord, pas à l'API bot).
# Cette commande recrée l'effet recherché : un salon vocal privé, visible
# uniquement par la personne appelée et la Team DTK, où chacun peut entrer
# et sortir librement (donc "s'appeler" dans les deux sens).
# ---------------------------------------------------------------------------

async def generate_tts_audio(text: str) -> str:
    """Génère un fichier audio (mp3) à partir d'un texte."""
    path = f"/tmp/tts_{int(time.time() * 1000)}.mp3"
    tts = gTTS(text=text, lang="fr")
    await asyncio.to_thread(tts.save, path)
    return path


async def play_in_voice_channel(voice_channel: discord.VoiceChannel, text: str):
    """Fait rejoindre le salon vocal par le bot, joue un message, puis ressort.
    Réutilise une connexion vocale existante si le bot est déjà connecté dans
    ce serveur, et se déconnecte toujours proprement même en cas d'erreur."""
    audio_path = None
    guild = voice_channel.guild
    vc = guild.voice_client
    try:
        if vc and vc.is_connected():
            await vc.move_to(voice_channel)
        else:
            vc = await voice_channel.connect()

        audio_path = await generate_tts_audio(text)
        vc.play(discord.FFmpegPCMAudio(audio_path))
        while vc.is_playing():
            await asyncio.sleep(1)
    finally:
        if vc and vc.is_connected():
            try:
                await vc.disconnect(force=True)
            except Exception:
                log.exception("Erreur lors de la déconnexion du salon vocal")
        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)


async def generate_call_announcement() -> str:
    """Génère un fichier audio (mp3) avec le message d'accueil de l'appel."""
    text = (
        "Bonjour, un membre de la Team D T K va prendre votre appel en charge. "
        "Merci de patienter. Vous pouvez nous appeler à tout moment, "
        "et nous pouvons également vous appeler."
    )
    return await generate_tts_audio(text)


# État global du service d'appel : True = ouvert, False = fermé.
# ⚠️ Cette valeur est réinitialisée à True à chaque redémarrage du bot
# (par exemple lors d'un redéploiement Railway).
call_service_open = True


@bot.command(name="closecalls")
@commands.has_permissions(administrator=True)
@commands.guild_only()
async def close_calls(ctx: commands.Context):
    """Ferme le service d'appel : !call sera refusé jusqu'à !opencalls."""
    global call_service_open
    call_service_open = False
    await ctx.send("🔴 Le service d'appel (`!call`) est maintenant **fermé**.")
    log.info(f"[Service d'appel fermé] par {ctx.author} ({ctx.author.id})")


@close_calls.error
async def close_calls_error(ctx: commands.Context, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Tu dois être administrateur pour utiliser cette commande.")
    elif isinstance(error, commands.NoPrivateMessage):
        await ctx.send("❌ Cette commande doit être utilisée dans un serveur, pas en DM.")
    else:
        raise error


@bot.command(name="opencalls")
@commands.has_permissions(administrator=True)
@commands.guild_only()
async def open_calls(ctx: commands.Context):
    """Rouvre le service d'appel."""
    global call_service_open
    call_service_open = True
    await ctx.send("🟢 Le service d'appel (`!call`) est maintenant **ouvert**.")
    log.info(f"[Service d'appel rouvert] par {ctx.author} ({ctx.author.id})")


@open_calls.error
async def open_calls_error(ctx: commands.Context, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Tu dois être administrateur pour utiliser cette commande.")
    elif isinstance(error, commands.NoPrivateMessage):
        await ctx.send("❌ Cette commande doit être utilisée dans un serveur, pas en DM.")
    else:
        raise error


# Salons en attente qu'un membre de la Team DTK les rejoigne :
# {channel_id: asyncio.Event}
waiting_calls: dict = {}


async def play_call_intro(voice_channel: discord.VoiceChannel, max_wait_seconds: float = 1800):
    """Joue la musique d'attente en boucle JUSQU'À ce qu'un membre de la Team
    DTK (ou un admin) rejoigne le salon, puis l'interrompt et annonce la prise
    en charge. Une limite de sécurité (30 min par défaut) évite que le bot
    reste connecté indéfiniment si personne ne répond."""
    guild = voice_channel.guild
    vc = guild.voice_client
    announce_path = None
    event = asyncio.Event()
    waiting_calls[voice_channel.id] = event

    # Si un membre de la Team DTK est déjà présent au moment où l'appel démarre
    if any(is_staff(m) for m in voice_channel.members if not m.bot):
        event.set()

    try:
        if vc and vc.is_connected():
            await vc.move_to(voice_channel)
        else:
            vc = await voice_channel.connect()

        # Musique d'attente en boucle, jusqu'à l'arrivée de la Team DTK (ou expiration)
        music_path = get_hold_music_path()
        vc.play(discord.FFmpegPCMAudio(music_path, before_options="-stream_loop -1"))

        try:
            await asyncio.wait_for(event.wait(), timeout=max_wait_seconds)
            timed_out = False
        except asyncio.TimeoutError:
            timed_out = True

        vc.stop()

        # Message final
        if timed_out:
            text = (
                "Aucun membre de la Team D T K n'a pu prendre votre appel pour le moment. "
                "Merci de réessayer plus tard."
            )
        else:
            text = "Un membre de la Team D T K a pris votre appel en charge !"

        announce_path = await generate_tts_audio(text)
        vc.play(discord.FFmpegPCMAudio(announce_path))
        while vc.is_playing():
            await asyncio.sleep(1)
    finally:
        waiting_calls.pop(voice_channel.id, None)
        if vc and vc.is_connected():
            try:
                await vc.disconnect(force=True)
            except Exception:
                log.exception("Erreur lors de la déconnexion du salon vocal")
        if announce_path and os.path.exists(announce_path):
            os.remove(announce_path)


@bot.command(name="call")
@commands.guild_only()
async def call_user(ctx: commands.Context, member: discord.Member = None):
    """
    Ouvre un appel privé avec la Team DTK.
    - Sans argument : ouvre un appel pour toi-même (accessible à tout le monde).
    - Avec un membre en argument : ouvre un appel ciblant ce membre
      (réservé aux administrateurs).
    """
    if member is None:
        member = ctx.author
    elif not ctx.author.guild_permissions.administrator:
        await ctx.send(
            "❌ Tu ne peux pas ouvrir un appel pour quelqu'un d'autre. "
            "Utilise `!call` sans argument pour ouvrir ton propre appel avec la Team DTK."
        )
        return

    if not call_service_open:
        await ctx.send(
            "📞 Le service d'appel est actuellement **fermé**. Merci de réessayer plus tard."
        )

        requester = ctx.author
        voice_channel = requester.voice.channel if requester.voice else None

        if voice_channel:
            try:
                await play_in_voice_channel(
                    voice_channel,
                    "Nos services d'appel sont fermés. Veuillez rappeler plus tard.",
                )
            except Exception:
                log.exception("Erreur lors de la lecture du message de fermeture")

            try:
                # Exclut la personne du salon vocal
                if requester.voice and requester.voice.channel:
                    await requester.move_to(None)
            except discord.Forbidden:
                log.warning(
                    f"Impossible d'exclure {requester} du vocal : permission "
                    "'Déplacer des membres' manquante."
                )
        return

    guild = ctx.guild
    category = guild.get_channel(CALL_CATEGORY_ID) if CALL_CATEGORY_ID else None

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False, connect=False),
        member: discord.PermissionOverwrite(view_channel=True, connect=True, speak=True),
        guild.me: discord.PermissionOverwrite(view_channel=True, connect=True, speak=True),
    }
    for staff_role_id in STAFF_ROLE_IDS:
        staff_role = guild.get_role(staff_role_id)
        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(
                view_channel=True, connect=True, speak=True
            )

    channel_name = f"appel-{member.name}"[:100]

    try:
        voice_channel = await guild.create_voice_channel(
            channel_name, overwrites=overwrites, category=category
        )
    except discord.Forbidden:
        await ctx.send("❌ Le bot n'a pas la permission de créer un salon vocal.")
        return
    except Exception as e:
        await ctx.send(f"❌ Erreur lors de la création du salon : {e}")
        log.exception("Erreur lors de la création du salon d'appel")
        return

    staff_pings = " ".join(
        guild.get_role(rid).mention for rid in STAFF_ROLE_IDS if guild.get_role(rid)
    )
    await ctx.send(
        f"📞 Salon d'appel privé créé pour {member.mention} : {voice_channel.mention} {staff_pings}"
    )

    if member != ctx.author:
        try:
            await member.send(
                f"📞 Un appel privé a été ouvert pour toi sur **{guild.name}**.\n"
                f"Rejoins le salon vocal **{voice_channel.name}** quand tu veux — "
                "un membre de la Team DTK va prendre ton appel en charge."
            )
        except discord.Forbidden:
            pass  # La personne a fermé ses DM — on continue quand même

    # Le bot rejoint le salon : musique d'attente quelques secondes, puis
    # annonce qu'un membre de la Team DTK a pris l'appel en charge
    try:
        await play_call_intro(voice_channel)
    except Exception:
        log.exception("Erreur lors de la lecture du message vocal d'accueil")


@call_user.error
async def call_user_error(ctx: commands.Context, error):
    if isinstance(error, commands.MemberNotFound):
        await ctx.send("❌ Membre introuvable. Mentionne-le (@membre) ou donne son ID.")
    elif isinstance(error, commands.NoPrivateMessage):
        await ctx.send("❌ Cette commande doit être utilisée dans un serveur, pas en DM.")
    else:
        raise error


# ---------------------------------------------------------------------------
# Mettre un appel en attente / le reprendre
# Usage : !hold [@membre]     (sans argument = ton propre salon vocal actuel)
#         !unhold [@membre]
#
# Met en sourdine (server mute) les membres qui ne font pas partie de la
# Team DTK dans le salon vocal ciblé, et joue un message vocal expliquant
# la mise en attente. !unhold fait l'inverse.
# ---------------------------------------------------------------------------

def resolve_voice_channel(ctx: commands.Context, member: discord.Member = None):
    """Détermine le salon vocal ciblé : celui du membre donné, sinon celui de l'auteur de la commande."""
    if member and member.voice:
        return member.voice.channel
    if ctx.author.voice:
        return ctx.author.voice.channel
    return None


def is_staff(member: discord.Member) -> bool:
    """Vrai si le membre a l'un des rôles Team DTK configurés, ou est administrateur."""
    if member.guild_permissions.administrator:
        return True
    if not STAFF_ROLE_IDS:
        return False
    return any(role.id in STAFF_ROLE_IDS for role in member.roles)


# Salons actuellement en attente : {guild_id: {"voice_client": vc, "music_path": str}}
active_holds: dict = {}


def get_hold_music_path() -> str:
    """Renvoie le chemin d'un fichier audio à utiliser comme musique d'attente.
    Si un fichier assets/hold_music.mp3 existe dans le projet, il est utilisé
    en priorité. Sinon, une petite mélodie douce est générée automatiquement
    (aucun droit d'auteur, générée localement)."""
    custom_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "assets", "hold_music.mp3"
    )
    if os.path.exists(custom_path):
        return custom_path
    return ensure_generated_hold_music()


def ensure_generated_hold_music() -> str:
    """Génère (une seule fois, puis met en cache) une courte mélodie douce en boucle."""
    generated_path = "/tmp/hold_music_generated.wav"
    if os.path.exists(generated_path):
        return generated_path

    import wave
    import struct
    import math as _math

    framerate = 44100
    notes = [261.63, 329.63, 392.00, 329.63]  # petit arpège doux (Do-Mi-Sol-Mi)
    note_duration = 0.5
    volume = 0.18

    frames = bytearray()
    for note_freq in notes:
        n_samples = int(framerate * note_duration)
        fade_samples = int(framerate * 0.05)
        for i in range(n_samples):
            t = i / framerate
            fade = min(1.0, i / fade_samples, (n_samples - i) / fade_samples)
            sample = volume * fade * _math.sin(2 * _math.pi * note_freq * t)
            frames += struct.pack("<h", int(sample * 32767))

    with wave.open(generated_path, "w") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(framerate)
        wav_file.writeframes(frames)

    return generated_path


@bot.command(name="hold")
@commands.has_permissions(administrator=True)  # restreint aux admins — à ajuster
@commands.guild_only()
async def hold_call(ctx: commands.Context, member: discord.Member = None):
    """Met l'appel en attente : sourdine des non-staff + musique d'attente en boucle."""
    voice_channel = resolve_voice_channel(ctx, member)

    if voice_channel is None:
        await ctx.send(
            "❌ Aucun salon vocal ciblé. Connecte-toi à un salon vocal, ou précise "
            "un membre déjà connecté : `!hold @membre`."
        )
        return

    guild = ctx.guild
    if guild.id in active_holds:
        await ctx.send("⚠️ Un appel est déjà en attente sur ce serveur. Utilise `!unhold` d'abord.")
        return

    muted = []
    vc = None
    try:
        for vc_member in voice_channel.members:
            if vc_member.bot or is_staff(vc_member):
                continue
            if not vc_member.voice.mute:
                try:
                    await vc_member.edit(mute=True)
                    muted.append(vc_member)
                except discord.Forbidden:
                    pass

        # Connexion (ou déplacement) du bot dans le salon vocal
        existing_vc = guild.voice_client
        if existing_vc and existing_vc.is_connected():
            await existing_vc.move_to(voice_channel)
            vc = existing_vc
        else:
            vc = await voice_channel.connect()

        # Message d'annonce de mise en attente
        announce_path = await generate_tts_audio(
            "Votre appel a été mis en attente. Merci de patienter, "
            "un membre de la Team D T K va reprendre la conversation."
        )
        vc.play(discord.FFmpegPCMAudio(announce_path))
        while vc.is_playing():
            await asyncio.sleep(1)
        os.remove(announce_path)

        # Musique d'attente, jouée en boucle jusqu'à !unhold
        music_path = get_hold_music_path()
        vc.play(discord.FFmpegPCMAudio(music_path, before_options="-stream_loop -1"))
        active_holds[guild.id] = {"voice_client": vc, "music_path": music_path}

        await ctx.send(
            f"⏸️ Appel mis en attente dans **{voice_channel.name}** "
            f"({len(muted)} membre(s) mis en sourdine) — musique d'attente lancée."
        )
        log.info(f"[Appel en attente] {voice_channel.name} — {len(muted)} membre(s) mis en sourdine")
    except discord.Forbidden:
        await ctx.send("❌ Le bot n'a pas la permission de gérer ce salon vocal.")
        if vc and vc.is_connected():
            await vc.disconnect(force=True)
    except Exception as e:
        await ctx.send(f"❌ Erreur : {e}")
        log.exception("Erreur lors de la mise en attente de l'appel")
        if vc and vc.is_connected():
            await vc.disconnect(force=True)
        active_holds.pop(guild.id, None)


@hold_call.error
async def hold_call_error(ctx: commands.Context, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Tu dois être administrateur pour utiliser cette commande.")
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send("❌ Membre introuvable. Mentionne-le (@membre) ou donne son ID.")
    elif isinstance(error, commands.NoPrivateMessage):
        await ctx.send("❌ Cette commande doit être utilisée dans un serveur, pas en DM.")
    else:
        raise error


@bot.command(name="unhold")
@commands.has_permissions(administrator=True)  # restreint aux admins — à ajuster
@commands.guild_only()
async def unhold_call(ctx: commands.Context, member: discord.Member = None):
    """Reprend l'appel : arrête la musique d'attente, lève la sourdine des non-staff + message vocal."""
    voice_channel = resolve_voice_channel(ctx, member)

    if voice_channel is None:
        await ctx.send(
            "❌ Aucun salon vocal ciblé. Connecte-toi à un salon vocal, ou précise "
            "un membre déjà connecté : `!unhold @membre`."
        )
        return

    guild = ctx.guild
    hold_info = active_holds.pop(guild.id, None)

    unmuted = []
    try:
        for vc_member in voice_channel.members:
            if vc_member.bot or is_staff(vc_member):
                continue
            if vc_member.voice.mute:
                try:
                    await vc_member.edit(mute=False)
                    unmuted.append(vc_member)
                except discord.Forbidden:
                    pass

        vc = guild.voice_client
        if vc and vc.is_connected():
            vc.stop()  # coupe la musique d'attente en cours
            if vc.channel.id != voice_channel.id:
                await vc.move_to(voice_channel)
        else:
            vc = await voice_channel.connect()

        resume_path = await generate_tts_audio(
            "Merci de votre patience. Un membre de la Team D T K "
            "reprend votre appel dès maintenant."
        )
        vc.play(discord.FFmpegPCMAudio(resume_path))
        while vc.is_playing():
            await asyncio.sleep(1)
        os.remove(resume_path)
        await vc.disconnect(force=True)

        await ctx.send(
            f"▶️ Appel repris dans **{voice_channel.name}** "
            f"({len(unmuted)} membre(s) démis de sourdine)."
        )
        log.info(f"[Appel repris] {voice_channel.name} — {len(unmuted)} membre(s) démis de sourdine")
    except discord.Forbidden:
        await ctx.send("❌ Le bot n'a pas la permission de gérer ce salon vocal.")
    except Exception as e:
        await ctx.send(f"❌ Erreur : {e}")
        log.exception("Erreur lors de la reprise de l'appel")


@unhold_call.error
async def unhold_call_error(ctx: commands.Context, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Tu dois être administrateur pour utiliser cette commande.")
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send("❌ Membre introuvable. Mentionne-le (@membre) ou donne son ID.")
    elif isinstance(error, commands.NoPrivateMessage):
        await ctx.send("❌ Cette commande doit être utilisée dans un serveur, pas en DM.")
    else:
        raise error


@bot.event
async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    # Déclenche la fin de l'attente si un membre de la Team DTK rejoint un
    # salon d'appel en cours de mise en attente (musique !call en cours).
    if (
        after.channel is not None
        and not member.bot
        and is_staff(member)
        and after.channel.id in waiting_calls
    ):
        waiting_calls[after.channel.id].set()

    # Supprime automatiquement un salon d'appel une fois qu'il est vide depuis 30 secondes.
    channel = before.channel
    if channel is None or not channel.name.startswith("appel-"):
        return

    await asyncio.sleep(30)

    # Re-vérifie que le salon existe toujours et est toujours vide avant de le supprimer
    refreshed = discord.utils.get(channel.guild.voice_channels, id=channel.id)
    if refreshed and len(refreshed.members) == 0:
        try:
            await refreshed.delete()
            log.info(f"[Salon d'appel supprimé] {refreshed.name}")
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Lancement du bot
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError(
            "DISCORD_TOKEN manquant. Crée un fichier .env avec DISCORD_TOKEN=ton_token"
        )
    bot.run(TOKEN)
