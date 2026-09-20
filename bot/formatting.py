"""Builds the discord.Embed objects posted to the channel.

Kept separate from the cogs/tasks that decide *when* to post, so the
message layout can be tweaked without touching any scheduling logic.
"""

import discord

BRAND_COLOR = discord.Color.dark_gold()


def team_name(team) -> str:
    return getattr(team, "team_name", None) or getattr(team, "team_abbrev", "Unknown")


def _bye_week_matchup(box_score) -> bool:
    return not box_score.away_team or not box_score.home_team


def build_recap_embed(week: int, box_scores: list) -> discord.Embed:
    embed = discord.Embed(
        title=f"Week {week} Recap",
        color=BRAND_COLOR,
    )

    biggest_blowout = None
    closest_game = None
    lines = []

    for bs in box_scores:
        if _bye_week_matchup(bs):
            continue

        home, away = team_name(bs.home_team), team_name(bs.away_team)
        home_score, away_score = bs.home_score, bs.away_score
        margin = abs(home_score - away_score)

        if home_score >= away_score:
            line = f"**{home} {home_score:.1f}** – {away_score:.1f} {away}"
        else:
            line = f"{home} {home_score:.1f} – **{away_score:.1f} {away}**"
        lines.append(line)

        if biggest_blowout is None or margin > biggest_blowout[0]:
            biggest_blowout = (margin, f"{home} vs {away} (by {margin:.1f})")
        if closest_game is None or margin < closest_game[0]:
            closest_game = (margin, f"{home} vs {away} (by {margin:.1f})")

    embed.description = "\n".join(lines) if lines else "No matchups found for this week."

    if biggest_blowout:
        embed.add_field(name="Biggest Blowout", value=biggest_blowout[1], inline=True)
    if closest_game:
        embed.add_field(name="Closest Game", value=closest_game[1], inline=True)

    return embed


def build_standings_embed(teams: list) -> discord.Embed:
    embed = discord.Embed(title="Standings", color=BRAND_COLOR)
    lines = []
    for i, team in enumerate(teams, start=1):
        record = f"{team.wins}-{team.losses}"
        if getattr(team, "ties", 0):
            record += f"-{team.ties}"
        lines.append(f"{i}. **{team_name(team)}** ({record}) — {team.points_for:.1f} pts")
    embed.description = "\n".join(lines) if lines else "No teams found."
    return embed


def build_preview_embed(week: int, box_scores: list) -> discord.Embed:
    embed = discord.Embed(
        title=f"Week {week} Matchup Preview",
        color=BRAND_COLOR,
    )
    lines = []
    for bs in box_scores:
        if _bye_week_matchup(bs):
            continue
        home, away = team_name(bs.home_team), team_name(bs.away_team)
        home_proj = getattr(bs, "home_projected", None)
        away_proj = getattr(bs, "away_projected", None)
        if home_proj is not None and away_proj is not None:
            lines.append(f"{home} (proj {home_proj:.1f}) vs {away} (proj {away_proj:.1f})")
        else:
            lines.append(f"{home} vs {away}")
    embed.description = "\n".join(lines) if lines else "No matchups found for this week."
    return embed


def build_lead_change_embed(home_name: str, away_name: str, home_score: float, away_score: float) -> discord.Embed:
    leader = home_name if home_score >= away_score else away_name
    embed = discord.Embed(
        title="Lead Change",
        description=f"**{leader}** takes the lead: {home_name} {home_score:.1f} – {away_score:.1f} {away_name}",
        color=discord.Color.blue(),
    )
    return embed


def build_close_game_embed(home_name: str, away_name: str, home_score: float, away_score: float) -> discord.Embed:
    margin = abs(home_score - away_score)
    embed = discord.Embed(
        title="Nail-Biter",
        description=f"{home_name} {home_score:.1f} – {away_score:.1f} {away_name} (margin: {margin:.1f})",
        color=discord.Color.red(),
    )
    return embed
