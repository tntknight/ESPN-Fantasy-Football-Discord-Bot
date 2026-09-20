# ESPN Fantasy Football Discord Bot

Posts weekly recaps, matchup previews, and live score/lead-change alerts for
a private (or public) ESPN Fantasy Football league into a Discord channel.
Also exposes `/standings`, `/recap`, `/preview`, and `/live` slash commands
for on-demand use.

## How it's put together

```
main.py              entrypoint: builds the bot, loads cogs, logs in
bot/config.py         reads all settings from environment variables
bot/espn_client.py    thin wrapper around the espn_api League object
bot/state.py          tiny JSON file so the bot remembers what it already posted
bot/formatting.py     builds the Discord embeds (edit this to change message layout)
bot/cogs/recap.py     weekly recap: scheduled task + /recap command
bot/cogs/preview.py   matchup preview: scheduled task + /preview command
bot/cogs/live.py      live lead-change / close-game alerts: scheduled task + /live command
bot/cogs/standings.py /standings command
```

Each cog is independent -- if you only want two of the four features, just
remove its entry from `COGS` in `main.py`.

## 1. Create the Discord bot

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications) -> **New Application**.
2. **Bot** tab -> **Reset Token** and copy it -> this is `DISCORD_TOKEN`. No privileged intents need to be enabled (the bot never reads message content).
3. **OAuth2 -> URL Generator**: scopes = `bot`, `applications.commands`; bot permissions = `Send Messages`, `Embed Links`. Open the generated URL and invite it to your server.
4. In Discord, enable Developer Mode (User Settings -> Advanced), right-click the channel you want updates in -> **Copy Channel ID** -> this is `DISCORD_CHANNEL_ID`.

## 2. Get your ESPN league info

- `ESPN_LEAGUE_ID`: the number in your league's URL, e.g. `fantasy.espn.com/football/league?leagueId=123456`.
- `ESPN_YEAR`: the season year, e.g. `2026`.
- Private league only -- `ESPN_SWID` / `ESPN_S2`: log into fantasy.espn.com in a browser, open DevTools -> Application (Chrome) / Storage (Firefox) -> Cookies -> `https://fantasy.espn.com`, and copy the `SWID` and `espn_s2` values. `SWID` includes the curly braces, e.g. `{ABC123...}`.

## 3. Configure

Copy `.env.example` to `.env` and fill in the values above. The scheduling
knobs (`RECAP_DAY`, `PREVIEW_DAY`, etc.) all have sensible defaults -- see
the comments in `.env.example`.

## 4. Run locally

```bash
python -m venv .venv
source .venv/bin/activate   # .venv\Scripts\activate on Windows
pip install -r requirements.txt
python main.py
```

Once it's running, try `/standings` in Discord to confirm the ESPN + Discord
connections both work end-to-end.

## 5. Deploy to Railway

1. Push this folder to a GitHub repo.
2. In Railway: **New Project -> Deploy from GitHub repo**, pick the repo.
3. Railway auto-detects Python via Nixpacks and reads `railway.json`, which sets the start command to `python main.py`.
4. In the service's **Variables** tab, add every variable from `.env.example` (do *not* commit your real `.env` -- it's gitignored).
5. Deploy. Check the **Deployments -> Logs** tab for `Logged in as ...` to confirm it connected.

Note: Railway's filesystem resets on every redeploy, so `state.json` (which
tracks "already posted this week") resets too -- that just means you might
get a duplicate recap/preview post right after a redeploy, never a missed one.

## Tuning the live-alert heuristic

`bot/cogs/live.py` only polls during a rough NFL game window (Thu/Sun/Mon,
configurable via `GAME_DAYS`/`GAME_WINDOW_HOURS` at the top of that file) and
flags a lead change or a margin under `LIVE_CLOSE_MARGIN` points. It's not
tied to real game-clock data (ESPN's fantasy API doesn't reliably expose
that), so treat it as a starting point to refine rather than a finished
feature.
