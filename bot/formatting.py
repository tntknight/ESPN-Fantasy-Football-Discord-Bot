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


# Mirrors live.py's BENCHED_SLOTS -- kept separate rather than imported to
# avoid a formatting.py <-> cogs.live circular import.
BENCHED_SLOTS = {"BE", "IR"}


def build_recap_embed(week: int, box_scores: list) -> discord.Embed:
    embed = discord.Embed(
        title=f"Week {week} Recap",
        color=BRAND_COLOR,
    )

    biggest_blowout = None
    closest_game = None
    top_team = None
    top_player = None
    top_bench_player = None
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

        for fantasy_team, score in ((bs.home_team, home_score), (bs.away_team, away_score)):
            if top_team is None or score > top_team[0]:
                top_team = (score, team_name(fantasy_team))

        for fantasy_team, lineup in ((bs.home_team, bs.home_lineup), (bs.away_team, bs.away_lineup)):
            for player in lineup:
                if top_player is None or player.points > top_player[0]:
                    top_player = (player.points, player.name, team_name(fantasy_team))
                if player.slot_position in BENCHED_SLOTS:
                    if top_bench_player is None or player.points > top_bench_player[0]:
                        top_bench_player = (player.points, player.name, team_name(fantasy_team))

    embed.description = "\n".join(lines) if lines else "No matchups found for this week."

    if biggest_blowout:
        embed.add_field(name="Biggest Blowout", value=biggest_blowout[1], inline=True)
    if closest_game:
        embed.add_field(name="Closest Game", value=closest_game[1], inline=True)
    if top_team:
        score, name = top_team
        embed.add_field(name="Highest Score", value=f"{name} ({score:.1f})", inline=True)
    if top_player:
        points, name, fantasy_team = top_player
        embed.add_field(name="Top Performer", value=f"{name} ({fantasy_team}) — {points:.1f} pts", inline=True)
    if top_bench_player:
        points, name, fantasy_team = top_bench_player
        embed.add_field(
            name="Best Player on the Bench", value=f"{name} ({fantasy_team}) — {points:.1f} pts", inline=True
        )

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


def build_live_scores_embed(week: int, box_scores: list) -> discord.Embed:
    embed = discord.Embed(
        title=f"Week {week} Live Scores",
        color=BRAND_COLOR,
    )
    lines = []
    for bs in box_scores:
        if _bye_week_matchup(bs):
            continue
        home, away = team_name(bs.home_team), team_name(bs.away_team)
        home_score, away_score = bs.home_score, bs.away_score
        if home_score >= away_score:
            line = f"**{home} {home_score:.1f}** – {away_score:.1f} {away}"
        else:
            line = f"{home} {home_score:.1f} – **{away_score:.1f} {away}**"
        lines.append(line)
    embed.description = "\n".join(lines) if lines else "No matchups found for this week."
    return embed


BIG_PLAY_YARDS = 50


def build_touchdown_embed(
    player_name: str, pro_team: str, fantasy_team_name: str, td_label: str, yards: float | None = None
) -> discord.Embed:
    yardage_text = f" for {yards:.0f} yards" if yards is not None else ""
    big_play = yards is not None and yards > BIG_PLAY_YARDS

    if big_play:
        embed = discord.Embed(
            title="🚨 HUGE TOUCHDOWN! 🚨",
            description=(
                f"**{player_name}** ({pro_team}) {td_label}{yardage_text}!!\n"
                f"Rostered by **{fantasy_team_name}**"
            ),
            color=discord.Color.gold(),
        )
        embed.set_footer(text=f"{yards:.0f}-yard house call")
    else:
        embed = discord.Embed(
            title="Touchdown!",
            description=f"**{player_name}** ({pro_team}) {td_label}{yardage_text} — rostered by **{fantasy_team_name}**",
            color=discord.Color.orange(),
        )
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
