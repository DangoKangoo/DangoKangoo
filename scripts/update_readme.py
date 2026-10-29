"""Refresh the live stats sentence and "Recently shipped" list in README.md.

Run by .github/workflows/readme.yml. Needs GITHUB_TOKEN; set INCLUDE_PRIVATE=true
(with a token that can read private repos) to list work from private repos too.
"""
import json
import os
import re
import sys
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

USER = os.environ.get("PROFILE_USER", "DangoKangoo")
TOKEN = os.environ["GITHUB_TOKEN"]
INCLUDE_PRIVATE = os.environ.get("INCLUDE_PRIVATE", "false").lower() == "true"
README = Path(sys.argv[1] if len(sys.argv) > 1 else "README.md")
ACTIVITY_LIMIT = 5
PER_REPO_LIMIT = 2


def graphql(query, variables=None):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables or {}}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as resp:
        body = json.load(resp)
    if "errors" in body:
        raise RuntimeError(f"GitHub API error: {body['errors']}")
    return body["data"]


def fetch_profile():
    return graphql(
        """query($login: String!) {
          user(login: $login) {
            createdAt
            pullRequests { totalCount }
            repositoriesContributedTo(contributionTypes: [COMMIT, PULL_REQUEST], includeUserRepositories: true) { totalCount }
            contributionsCollection {
              contributionCalendar { weeks { contributionDays { date contributionCount } } }
            }
          }
        }""",
        {"login": USER},
    )["user"]


def total_contributions(created_at):
    start_year = int(created_at[:4])
    this_year = date.today().year
    fields = "\n".join(
        f'y{y}: contributionsCollection(from: "{y}-01-01T00:00:00Z", to: "{y}-12-31T23:59:59Z") '
        f"{{ contributionCalendar {{ totalContributions }} }}"
        for y in range(start_year, this_year + 1)
    )
    data = graphql(f'query($login: String!) {{ user(login: $login) {{ {fields} }} }}', {"login": USER})["user"]
    return sum(v["contributionCalendar"]["totalContributions"] for v in data.values())


def current_streak(calendar):
    counts = {d["date"]: d["contributionCount"] for w in calendar["weeks"] for d in w["contributionDays"]}
    day = date.today()
    # Today not counting yet shouldn't break the streak
    if counts.get(day.isoformat(), 0) == 0:
        day -= timedelta(days=1)
    streak = 0
    while counts.get(day.isoformat(), 0) > 0:
        streak += 1
        day -= timedelta(days=1)
    return streak


def fetch_shipped():
    nodes = graphql(
        """query($q: String!) {
          search(query: $q, type: ISSUE, first: 100) {
            nodes { ... on PullRequest { title url mergedAt repository { nameWithOwner isPrivate } } }
          }
        }""",
        {"q": f"author:{USER} is:pr is:merged sort:updated-desc"},
    )["search"]["nodes"]
    nodes = [n for n in nodes if n and (INCLUDE_PRIVATE or not n["repository"]["isPrivate"])]
    nodes.sort(key=lambda n: n["mergedAt"], reverse=True)
    # Cap per repo so one busy repo doesn't fill the whole list
    picked, per_repo = [], {}
    for n in nodes:
        repo = n["repository"]["nameWithOwner"]
        if per_repo.get(repo, 0) < PER_REPO_LIMIT:
            per_repo[repo] = per_repo.get(repo, 0) + 1
            picked.append(n)
    return picked[:ACTIVITY_LIMIT]


def clean_title(title):
    # "feat(scope): add thing" -> "Add thing"
    title = re.sub(r"^\w+(\([^)]*\))?!?:\s*", "", title).strip()
    return title[:1].upper() + title[1:]


def ago(iso):
    days = (datetime.now(timezone.utc) - datetime.fromisoformat(iso.replace("Z", "+00:00"))).days
    if days == 0:
        return "today"
    if days == 1:
        return "yesterday"
    if days < 30:
        return f"{days} days ago"
    months = days // 30
    return f"{months} month{'s' if months > 1 else ''} ago"


def render_stats(profile, total):
    years = date.today().year - int(profile["createdAt"][:4])
    streak = current_streak(profile["contributionsCollection"]["contributionCalendar"])
    joined = f"**{years}** year{'s' if years != 1 else ''} ago" if years else "this year"
    return (
        f"I joined GitHub {joined} and have since made **{total:,}** contributions, "
        f"opened **{profile['pullRequests']['totalCount']}** pull requests and shipped work across "
        f"**{profile['repositoriesContributedTo']['totalCount']}** repositories. "
        f"Current streak: **{streak}** day{'s' if streak != 1 else ''}."
    )


def render_shipped(prs):
    if not prs:
        return "_Nothing public merged recently._"
    lines = []
    for pr in prs:
        repo = pr["repository"]
        # Private repos would 404 for visitors, so they get no link
        title = clean_title(pr["title"])
        if not repo["isPrivate"]:
            title = f"[{title}]({pr['url']})"
        lines.append(f"- {title} · `{repo['nameWithOwner']}` · {ago(pr['mergedAt'])}")
    return "\n".join(lines)


def replace_block(text, name, content):
    pattern = re.compile(rf"(<!-- {name}:START -->)(.*?)(<!-- {name}:END -->)", re.S)
    if not pattern.search(text):
        raise RuntimeError(f"README is missing the {name}:START/END markers")
    return pattern.sub(lambda m: f"{m.group(1)}\n{content}\n{m.group(3)}", text)


def main():
    profile = fetch_profile()
    text = README.read_text(encoding="utf-8")
    text = replace_block(text, "STATS", render_stats(profile, total_contributions(profile["createdAt"])))
    text = replace_block(text, "SHIPPED", render_shipped(fetch_shipped()))
    README.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
