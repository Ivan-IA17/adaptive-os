"""
Habit Tracker — learns the user's profile usage patterns over time.

Analyses historical data in StateDB to:
- Detect which profiles are used at which times/days
- Identify apps that reliably predict a profile switch
- Provide priors to the decision engine (boosts confidence for known patterns)
- Generate weekly usage summaries
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

import aiosqlite

from adaptive_os.core.state import StateDB

logger = logging.getLogger(__name__)


@dataclass
class UsagePattern:
    """A learned pattern: at (hour, day_of_week), profile X is used N% of the time."""

    hour: int
    day_of_week: int
    profile: str
    frequency: float  # 0.0 – 1.0 (fraction of observations)
    sample_count: int


@dataclass
class AppCorrelation:
    """App X running correlates with profile Y at this strength."""

    app: str
    profile: str
    correlation: float  # 0.0 – 1.0
    sample_count: int


@dataclass
class HabitSummary:
    """Aggregated learning summary for use by the DecisionEngine."""

    # time_priors[hour][day_of_week] = {profile: probability}
    time_priors: dict[int, dict[int, dict[str, float]]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
    )
    # app_correlations[app] = [(profile, correlation)]
    app_correlations: dict[str, list[tuple[str, float]]] = field(
        default_factory=lambda: defaultdict(list)
    )
    total_switches: int = 0
    most_used_profile: str = "work"
    days_tracked: int = 0

    def profile_prior_for_time(self, hour: int, day_of_week: int) -> dict[str, float]:
        """Return probability distribution over profiles for given time."""
        return dict(self.time_priors.get(hour, {}).get(day_of_week, {}))

    def top_app_profiles(self, app: str, n: int = 3) -> list[tuple[str, float]]:
        """Return top N (profile, correlation) pairs for an app."""
        correlations = self.app_correlations.get(app, [])
        return sorted(correlations, key=lambda x: x[1], reverse=True)[:n]

    def to_llm_hint(self, hour: int, day_of_week: int, active_apps: list[str]) -> str:
        """
        Generate a natural-language hint for the LLM prompt based on learned habits.
        This nudges the model towards historically accurate decisions.
        """
        hints: list[str] = []

        # Time-based prior
        time_prior = self.profile_prior_for_time(hour, day_of_week)
        if time_prior:
            top = max(time_prior, key=lambda p: time_prior[p])
            pct = int(time_prior[top] * 100)
            if pct >= 60:
                day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
                hints.append(
                    f"Historical pattern: at {hour:02d}:00 on {day_names[day_of_week]}, "
                    f"the user is in '{top}' mode {pct}% of the time."
                )

        # App-based correlations
        for app in active_apps[:5]:
            top_profiles = self.top_app_profiles(app, n=1)
            if top_profiles:
                profile, corr = top_profiles[0]
                if corr >= 0.7:
                    hints.append(
                        f"App '{app}' strongly correlates with '{profile}' profile "
                        f"({int(corr * 100)}% of past observations)."
                    )

        if not hints:
            return ""

        return "Learned habits:\n" + "\n".join(f"- {h}" for h in hints)


class HabitTracker:
    """
    Analyses StateDB history to learn usage patterns.
    Call `analyse()` periodically (e.g. every hour) to refresh the summary.
    """

    def __init__(self, state: StateDB) -> None:
        self._state = state
        self._summary: HabitSummary | None = None

    @property
    def summary(self) -> HabitSummary | None:
        return self._summary

    async def analyse(self, lookback_days: int = 30) -> HabitSummary:
        """
        Re-analyse the history and update the internal summary.
        Call this once per hour or after each profile switch.
        """
        since = (datetime.now(timezone.utc) - timedelta(days=lookback_days)).isoformat()

        switches = await self._fetch_switches(since)
        snapshots = await self._fetch_snapshots(since)

        summary = HabitSummary()
        summary.total_switches = len(switches)
        summary.days_tracked = min(lookback_days, self._days_since_first_switch(switches))

        # Build time priors
        time_counts: dict[int, dict[int, dict[str, int]]] = defaultdict(
            lambda: defaultdict(lambda: defaultdict(int))
        )
        for sw in switches:
            dt = datetime.fromisoformat(sw["switched_at"])
            time_counts[dt.hour][dt.weekday()][sw["profile"]] += 1

        for hour, days in time_counts.items():
            for dow, profiles in days.items():
                total = sum(profiles.values())
                for profile, count in profiles.items():
                    summary.time_priors[hour][dow][profile] = count / total

        # Build app correlations from context snapshots joined with switches
        app_profile_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        app_total_counts: dict[str, int] = defaultdict(int)

        for snap_data in snapshots:
            try:
                snap = json.loads(snap_data["snapshot"])
                recorded = datetime.fromisoformat(snap_data["recorded_at"])
                # Find the profile active within 30s of this snapshot
                active_profile = self._profile_at_time(switches, recorded)
                if not active_profile:
                    continue
                for app in snap.get("active_apps", []):
                    app_profile_counts[app][active_profile] += 1
                    app_total_counts[app] += 1
            except (json.JSONDecodeError, KeyError):
                continue

        for app, profile_counts in app_profile_counts.items():
            total = app_total_counts[app]
            if total < 5:  # Ignore apps with too few observations
                continue
            for profile, count in profile_counts.items():
                correlation = count / total
                summary.app_correlations[app].append((profile, correlation))

        # Most used profile
        profile_totals: dict[str, int] = defaultdict(int)
        for sw in switches:
            profile_totals[sw["profile"]] += 1
        if profile_totals:
            summary.most_used_profile = max(profile_totals, key=lambda p: profile_totals[p])

        self._summary = summary
        logger.info(
            "Habit analysis complete: %d switches, %d days tracked, most-used: %s",
            summary.total_switches,
            summary.days_tracked,
            summary.most_used_profile,
        )
        return summary

    async def weekly_report(self) -> str:
        """Generate a human-readable weekly usage report."""
        if not self._summary:
            await self.analyse(lookback_days=7)
        s = self._summary
        assert s is not None

        lines = [
            "📊 Weekly Adaptive OS Usage Report",
            "─" * 40,
            f"Total profile switches: {s.total_switches}",
            f"Most-used profile: {s.most_used_profile}",
            f"Days tracked: {s.days_tracked}",
            "",
            "Time patterns:",
        ]

        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        for hour in sorted(s.time_priors.keys()):
            for dow in sorted(s.time_priors[hour].keys()):
                priors = s.time_priors[hour][dow]
                top = max(priors, key=lambda p: priors[p])
                pct = int(priors[top] * 100)
                if pct >= 50:
                    lines.append(f"  {hour:02d}:00 {day_names[dow]} → {top} ({pct}%)")

        lines += ["", "Strong app correlations:"]
        shown = set()
        for app, correlations in sorted(s.app_correlations.items()):
            for profile, corr in sorted(correlations, key=lambda x: x[1], reverse=True):
                if corr >= 0.75 and app not in shown:
                    lines.append(f"  {app} → {profile} ({int(corr * 100)}%)")
                    shown.add(app)
                    break

        return "\n".join(lines)

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _fetch_switches(self, since: str) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self._state._path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT profile, switched_at FROM profile_history WHERE switched_at >= ? ORDER BY id",
                (since,),
            ) as cur:
                rows = await cur.fetchall()
                return [dict(r) for r in rows]

    async def _fetch_snapshots(self, since: str) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self._state._path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT snapshot, recorded_at FROM context_snapshots WHERE recorded_at >= ? ORDER BY id",
                (since,),
            ) as cur:
                rows = await cur.fetchall()
                return [dict(r) for r in rows]

    @staticmethod
    def _profile_at_time(
        switches: list[dict[str, Any]], at: datetime, window_seconds: int = 60
    ) -> str | None:
        """Find which profile was active at a given timestamp."""
        active = None
        for sw in switches:
            sw_time = datetime.fromisoformat(sw["switched_at"])
            if sw_time <= at + timedelta(seconds=window_seconds):
                active = sw["profile"]
            else:
                break
        return active

    @staticmethod
    def _days_since_first_switch(switches: list[dict[str, Any]]) -> int:
        if not switches:
            return 0
        first = datetime.fromisoformat(switches[0]["switched_at"])
        return max(1, (datetime.now(timezone.utc) - first).days)
