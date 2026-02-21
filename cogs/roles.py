"""Bulk and targeted role management commands."""

import discord
from discord.ext import commands
from discord import app_commands
import re
from typing import Optional, List

class Roles(commands.Cog):
    """Adds and removes roles with optional bulk assignment."""

    def __init__(self, client):
        self.client = client

    @app_commands.command(name="addrole", description="Aggiunge uno o più ruoli ad un membro oppure a tutti (no bot)")
    @app_commands.default_permissions(manage_roles=True)
    @app_commands.describe(
        roles="Menziona uno o più ruoli (separati da spazio)",
        member="Membro destinatario (richiesto se all=False)",
        all="Metti True per applicare a tutti gli utenti non bot"
    )
    async def addrole(self, interaction: discord.Interaction, roles: str, member: Optional[discord.Member] = None, all: bool = False):
        await interaction.response.defer(thinking=True)
        if not roles:
            return await interaction.followup.send("Devi menzionare almeno un ruolo.")
        role_ids = re.findall(r"<@&(\\d+)>", roles)
        unique_ids = list(dict.fromkeys(role_ids))
        if not unique_ids:
            return await interaction.followup.send("Non ho trovato menzioni di ruoli valide.")
        guild_roles: List[discord.Role] = []
        not_found: List[str] = []
        for rid in unique_ids:
            role_obj = interaction.guild.get_role(int(rid))
            if role_obj:
                guild_roles.append(role_obj)
            else:
                not_found.append(rid)
        if not guild_roles:
            return await interaction.followup.send("Nessun ruolo valido trovato nel server.")
        me = interaction.guild.me
        manageable_roles: List[discord.Role] = []
        unmanageable: List[discord.Role] = []
        can_manage_any = me.guild_permissions.manage_roles
        for r in guild_roles:
            try:
                flag = getattr(r, "is_assignable", None)
                if callable(flag):
                    assignable_ok = flag()
                else:
                    assignable_ok = True
            except Exception:
                assignable_ok = True
            if (not can_manage_any) or (r >= me.top_role) or (not assignable_ok):
                unmanageable.append(r)
            else:
                manageable_roles.append(r)
        if not manageable_roles:
            return await interaction.followup.send("Non posso assegnare nessuno dei ruoli indicati (ruoli più alti o non gestibili).")
        MAX_ROLES = 10
        if len(manageable_roles) > MAX_ROLES:
            manageable_roles = manageable_roles[:MAX_ROLES]
        if all:
            target_members = [m for m in interaction.guild.members if not m.bot]
            if interaction.guild.member_count and len(target_members) + 3 < interaction.guild.member_count:
                fetched = []
                async for m in interaction.guild.fetch_members(limit=None):
                    if not m.bot:
                        fetched.append(m)
                if fetched:
                    target_members = fetched
            if not target_members:
                return await interaction.followup.send("Non ci sono utenti umani a cui assegnare ruoli.")
        else:
            if member is None:
                return await interaction.followup.send("Devi specificare un membro oppure usare all=True.")
            if member.bot:
                return await interaction.followup.send("Non assegno ruoli ai bot.")
            target_members = [member]
        success = 0
        skipped_already = 0
        failed = 0
        role_assign_counts = {r: 0 for r in manageable_roles}
        debug_lines = []
        for tm in target_members:
            to_add = [r for r in manageable_roles if r not in tm.roles]
            if not to_add:
                skipped_already += 1
                debug_lines.append(f"SKIP {tm} (già ha tutti)")
                continue
            try:
                await tm.add_roles(*to_add, reason=f"Richiesto da {interaction.user} via /addrole")
                success += 1
                debug_lines.append(f"OK {tm}: +{' '.join(r.name for r in to_add)}")
                for r in to_add:
                    if r in role_assign_counts:
                        role_assign_counts[r] += 1
            except Exception as e:
                failed += 1
                debug_lines.append(f"FAIL {tm}: {e.__class__.__name__}")
        embed = discord.Embed(title="Assegnazione Ruoli", color=discord.Color.orange())
        embed.add_field(name="Ruoli richiesti", value=" ".join(r.mention for r in guild_roles), inline=False)
        if unmanageable:
            embed.add_field(name="Non gestibili", value=" ".join(r.mention for r in unmanageable), inline=False)
        if not_found:
            embed.add_field(name="ID non trovati", value=", ".join(not_found), inline=False)
        target_desc = f"tutti gli utenti non bot ({len(target_members)})" if all else target_members[0].mention
        embed.add_field(name="Destinatari", value=target_desc, inline=False)
        embed.add_field(name="Successi", value=str(success), inline=True)
        embed.add_field(name="Già li avevano", value=str(skipped_already), inline=True)
        embed.add_field(name="Falliti", value=str(failed), inline=True)
        if role_assign_counts:
            per_role_lines = []
            for r, c in role_assign_counts.items():
                per_role_lines.append(f"{r.mention}: {c}")
            per_role_text = "\n".join(per_role_lines)
            if len(per_role_text) > 1000:
                per_role_text = per_role_text[:1000] + "..."
            embed.add_field(name="Assegnazioni per ruolo", value=per_role_text, inline=False)
        embed.set_footer(text=f"Operazione richiesta da {interaction.user}")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="removerole", description="Remove a role from a member")
    @app_commands.default_permissions(manage_roles=True)
    async def removerole(self, interaction: discord.Interaction, member: discord.Member, *, role: discord.Role = None):
        embed_removerole = discord.Embed(title="", description=f"**{member}** was removed from **{role}**", color=discord.Color.dark_purple())
        await member.remove_roles(role)
        await interaction.response.send_message(embed=embed_removerole)

async def setup(client):
    """Register the cog in the bot instance."""
    await client.add_cog(Roles(client))
