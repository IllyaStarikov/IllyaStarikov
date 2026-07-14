#!/usr/bin/env python3
"""Fetch live GitHub stats for the neofetch README card.

Uses `gh api graphql` locally (the Action later uses GITHUB_TOKEN via requests).
Outputs stats.json with: uptime source date, repos, contributed, stars,
commits (all-time), followers, loc_add, loc_del, per-repo cache.
"""
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

USER = "IllyaStarikov"
HERE = Path(__file__).parent
CACHE = HERE / "loc_cache.json"


def gql(query, **variables):
    cmd = ["gh", "api", "graphql", "-f", f"query={query}"]
    for k, v in variables.items():
        flag = "-F" if isinstance(v, (int, bool)) else "-f"
        cmd += [flag, f"{k}={v}"]
    out = subprocess.run(cmd, capture_output=True, text=True)
    if out.returncode != 0:
        sys.exit(f"GraphQL error: {out.stderr[:500]}")
    return json.loads(out.stdout)["data"]


def base_stats():
    q = """
    query($login: String!) {
      user(login: $login) {
        id
        createdAt
        followers { totalCount }
        following { totalCount }
        repositories(first: 100, ownerAffiliations: OWNER) {
          totalCount
          nodes {
            nameWithOwner
            stargazerCount
            defaultBranchRef { target { ... on Commit { history(first: 0) { totalCount } oid } } }
          }
        }
        repositoriesContributedTo(first: 100, contributionTypes: [COMMIT, PULL_REQUEST, REPOSITORY, PULL_REQUEST_REVIEW]) {
          totalCount
        }
      }
    }"""
    return gql(q, login=USER)["user"]


def commits_all_time(created_at):
    """Sum contributionsCollection commit counts year-by-year since account creation."""
    q = """
    query($login: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $login) {
        contributionsCollection(from: $from, to: $to) {
          totalCommitContributions
          restrictedContributionsCount
        }
      }
    }"""
    start = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    total_public, total_restricted = 0, 0
    year = start
    while year < now:
        year_end = min(year.replace(year=year.year + 1), now)
        cc = gql(q, login=USER,
                 **{"from": year.isoformat(), "to": year_end.isoformat()})
        cc = cc["user"]["contributionsCollection"]
        total_public += cc["totalCommitContributions"]
        total_restricted += cc["restrictedContributionsCount"]
        year = year_end
    return total_public, total_restricted


def loc_for_repo(name_with_owner, user_id, head_oid, cached):
    """Walk default-branch history for commits authored by user, summing +/-."""
    if cached and cached.get("head") == head_oid:
        return cached  # branch unchanged since last run
    owner, name = name_with_owner.split("/")
    q = """
    query($owner: String!, $name: String!, $uid: ID!, $cursor: String) {
      repository(owner: $owner, name: $name) {
        defaultBranchRef {
          target {
            ... on Commit {
              history(first: 100, author: {id: $uid}, after: $cursor) {
                pageInfo { hasNextPage endCursor }
                nodes { additions deletions }
              }
            }
          }
        }
      }
    }"""
    add = rm = commits = 0
    cursor = None
    while True:
        variables = {"owner": owner, "name": name, "uid": user_id}
        if cursor:
            variables["cursor"] = cursor
        data = gql(q, **variables)
        ref = data["repository"]["defaultBranchRef"]
        if ref is None:  # empty repo
            break
        hist = ref["target"]["history"]
        for node in hist["nodes"]:
            add += node["additions"]
            rm += node["deletions"]
            commits += 1
        if not hist["pageInfo"]["hasNextPage"]:
            break
        cursor = hist["pageInfo"]["endCursor"]
    return {"head": head_oid, "add": add, "del": rm, "commits": commits}


def main():
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    user = base_stats()
    repos = user["repositories"]["nodes"]

    loc_add = loc_del = my_commits_on_branches = 0
    for repo in repos:
        nwo = repo["nameWithOwner"]
        ref = repo["defaultBranchRef"]
        head = ref["target"]["oid"] if ref else None
        result = loc_for_repo(nwo, user["id"], head, cache.get(nwo))
        cache[nwo] = result
        loc_add += result["add"]
        loc_del += result["del"]
        my_commits_on_branches += result["commits"]
        print(f"  {nwo}: +{result['add']:,} -{result['del']:,} "
              f"({result['commits']} commits)", file=sys.stderr)

    public_commits, restricted_commits = commits_all_time(user["createdAt"])

    stats = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "created_at": user["createdAt"],
        "followers": user["followers"]["totalCount"],
        "following": user["following"]["totalCount"],
        "repos": user["repositories"]["totalCount"],
        "contributed": user["repositoriesContributedTo"]["totalCount"],
        "stars": sum(r["stargazerCount"] for r in repos),
        "commits_public": public_commits,
        "commits_restricted": restricted_commits,
        "commits_total": public_commits + restricted_commits,
        "loc_add": loc_add,
        "loc_del": loc_del,
        "loc_net": loc_add - loc_del,
    }
    CACHE.write_text(json.dumps(cache, indent=2))
    (HERE / "stats.json").write_text(json.dumps(stats, indent=2))
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
