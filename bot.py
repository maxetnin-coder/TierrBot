import discord
from discord.ext import commands, tasks
import json
import os

# Mets ton vrai token entre les guillemets ici en local
TOKEN_DU_BOT = "TOKEN_SECRET" 


# Configuration de base du bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

DATA_FILE = "brawl_data.json"

# --- SYSTÈME DE SAUVEGARDE ---
def load_data():
    """Charge les données depuis le fichier JSON."""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_data(data):
    """Sauvegarde les données dans le fichier JSON."""
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# --- SYSTÈME DE RANGS (TIERS) ---
def get_tier(points):
    """Détermine le rang Brawl Stars en fonction des trophées."""
    if points < 500: return "🥉 Tier E"
    elif points < 1000: return "🥈 Tier D"
    elif points < 2000: return "🥇 Tier C"
    elif points < 3000: return "💎 Tier B"
    elif points < 5000: return "🟣 Tier A"
    elif points < 8000: return "🟡 Tier S"

# --- GÉNÉRATION DU CLASSEMENT ---
def generate_top_embed(guild):
    """Crée l'interface (Embed) du classement pour éviter de répéter le code."""
    data = load_data()
    embed = discord.Embed(title="🏆 Classement Permanent Brawl Stars 🏆", color=0xffd700)
    embed.set_footer(text="Actualisé automatiquement toutes les 5 minutes.")
    
    # On retire les données de configuration pour ne garder que les joueurs
    players_data = {k: v for k, v in data.items() if k != "config"}
    
    if not players_data:
        embed.description = "❌ Le classement est vide pour le moment !"
        return embed

    # Trie les joueurs
    sorted_users = sorted(players_data.items(), key=lambda x: x[1].get("points", 0), reverse=True)
    
    for index, (user_id, info) in enumerate(sorted_users[:10]):
        member = guild.get_member(int(user_id))
        name = member.display_name if member else "Joueur inconnu"
        points = info.get("points", 0)
        tier = get_tier(points)
        
        embed.add_field(name=f"#{index + 1} {name}", value=f"🏆 {points} | {tier}", inline=False)
        
    return embed

# --- ÉVÉNEMENTS ET COMMANDES ---
@bot.event
async def on_ready():
    print(f'✅ Bot connecté avec succès en tant que {bot.user}')
    # Lance la boucle d'actualisation si elle n'est pas déjà lancée
    if not update_leaderboard.is_running():
        update_leaderboard.start()

@bot.command(name="profil")
async def profil(ctx, member: discord.Member = None):
    """Affiche le profil d'un joueur."""
    member = member or ctx.author
    data = load_data()
    user_id = str(member.id)
    
    points = data.get(user_id, {}).get("points", 0)
    tier = get_tier(points)
    
    embed = discord.Embed(title=f"Profil Brawl Stars de {member.display_name}", color=0x00ff00)
    embed.add_field(name="Trophées", value=f"🏆 {points}", inline=False)
    embed.add_field(name="Rang actuel", value=tier, inline=False)
    
    if member.avatar:
        embed.set_thumbnail(url=member.avatar.url)
        
    await ctx.send(embed=embed)

@bot.command(name="add")
@commands.has_permissions(administrator=True)
async def addpoints(ctx, member: discord.Member, amount: int):
    """(Admin) Ajoute des trophées à un joueur."""
    data = load_data()
    user_id = str(member.id)
    
    if user_id not in data:
        data[user_id] = {"points": 0}
        
    data[user_id]["points"] += amount
    save_data(data)
    
    await ctx.send(f"✅ {amount} 🏆 ajoutés à {member.mention} ! (Nouveau total : {data[user_id]['points']})")

# --- NOUVEAUTÉ : CLASSEMENT PERMANENT ---

@bot.command(name="set_top")
@commands.has_permissions(administrator=True)
async def set_top(ctx):
    """(Admin) Définit le salon actuel pour afficher le classement permanent."""
    # Crée et envoie le premier message
    embed = generate_top_embed(ctx.guild)
    msg = await ctx.send(embed=embed)
    
    # Sauvegarde l'ID du salon et du message
    data = load_data()
    data["config"] = {
        "channel_id": ctx.channel.id,
        "message_id": msg.id,
        "guild_id": ctx.guild.id
    }
    save_data(data)
    
    # Petit message de confirmation qui s'efface tout seul au bout de 5 secondes
    await ctx.send("✅ Classement permanent initialisé ici !", delete_after=5)

@tasks.loop(minutes=5)
async def update_leaderboard():
    """Tâche en arrière-plan qui modifie le message toutes les 5 minutes."""
    data = load_data()
    config = data.get("config")
    
    # Si le classement n'a pas encore été configuré avec !set_top, on annule
    if not config:
        return
        
    # Récupère le serveur, le salon et le message
    guild = bot.get_guild(config["guild_id"])
    if not guild: return
    
    channel = guild.get_channel(config["channel_id"])
    if not channel: return
    
    try:
        msg = await channel.fetch_message(config["message_id"])
        # Régénère le classement avec les données actuelles
        embed = generate_top_embed(guild)
        # Modifie le message existant
        await msg.edit(embed=embed)
    except discord.NotFound:
        # Si quelqu'un a supprimé le message par erreur, on affiche une erreur dans la console
        print("Erreur : Le message du classement permanent a été supprimé.")

# --- DÉMARRAGE DU BOT ---
bot.run(TOKEN_DU_BOT)


