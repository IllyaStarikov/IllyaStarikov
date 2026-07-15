"""Tests for the GitHub-stats fetcher (network calls are mocked)."""

from unittest import mock

import pytest

import fetch_stats as fs


def test_gql_builds_command_and_parses():
    fake = mock.Mock(returncode=0, stdout='{"data": {"x": 1}}', stderr="")
    with mock.patch("fetch_stats.subprocess.run", return_value=fake) as run:
        out = fs.gql("QUERY", login="me", count=5)
    assert out == {"x": 1}
    cmd = run.call_args.args[0]
    assert cmd[:3] == ["gh", "api", "graphql"]
    assert "query=QUERY" in cmd
    # strings use -f, ints/bools use -F
    assert cmd[cmd.index("login=me") - 1] == "-f"
    assert cmd[cmd.index("count=5") - 1] == "-F"


def test_gql_exits_on_error():
    fake = mock.Mock(returncode=1, stdout="", stderr="boom")
    with mock.patch("fetch_stats.subprocess.run", return_value=fake):
        with pytest.raises(SystemExit):
            fs.gql("Q")


def test_base_stats_query_keeps_fields():
    with mock.patch("fetch_stats.gql", return_value={"user": {"ok": 1}}) as g:
        fs.base_stats()
    q = g.call_args.args[0]
    for field in (
        "repositoriesContributedTo",
        "defaultBranchRef",
        "stargazerCount",
        "createdAt",
        "PULL_REQUEST_REVIEW",
    ):
        assert field in q


def test_commits_all_time_sums_year_windows():
    resp = {
        "user": {
            "contributionsCollection": {
                "totalCommitContributions": 10,
                "restrictedContributionsCount": 3,
            }
        }
    }
    with mock.patch("fetch_stats.gql", return_value=resp) as g:
        public, restricted = fs.commits_all_time("2023-01-01T00:00:00Z")
    assert g.call_count >= 3  # 2023 -> now, one call per year window
    assert public == 10 * g.call_count
    assert restricted == 3 * g.call_count


def test_loc_for_repo_reuses_cache():
    cached = {"head": "abc123", "add": 5, "del": 2, "commits": 1}
    with mock.patch("fetch_stats.gql") as g:
        out = fs.loc_for_repo("owner/repo", "uid", "abc123", cached)
    assert out is cached
    g.assert_not_called()  # unchanged head -> zero API calls


def test_loc_for_repo_walks_history():
    page = {
        "repository": {
            "defaultBranchRef": {
                "target": {
                    "history": {
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                        "nodes": [
                            {"additions": 10, "deletions": 3},
                            {"additions": 5, "deletions": 1},
                        ],
                    }
                }
            }
        }
    }
    with mock.patch("fetch_stats.gql", return_value=page):
        out = fs.loc_for_repo("owner/repo", "uid", "newhead", None)
    assert out == {"head": "newhead", "add": 15, "del": 4, "commits": 2}


def test_loc_for_repo_handles_empty_repo():
    page = {"repository": {"defaultBranchRef": None}}
    with mock.patch("fetch_stats.gql", return_value=page):
        out = fs.loc_for_repo("owner/repo", "uid", "head", None)
    assert out == {"head": "head", "add": 0, "del": 0, "commits": 0}
