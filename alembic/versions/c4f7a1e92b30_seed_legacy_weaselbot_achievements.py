"""seed legacy weaselbot achievements

Backfills the canonical set of achievements that the deprecated WeaselBot
service awarded (see github.com/F3-Nation/archive-weaselbot), so that the
F3 Nation Slack Bot's auto-award engine can grant them.

The initial baseline (bc8d946e6cf2) only seeded three of these by name
(The Priest, The Monk, Leader of Men) and predates the auto-award columns,
so every seeded achievement has ``auto_award = false``. This migration:

1. Inserts the eleven remaining legacy achievements, and
2. Sets auto-award configuration (cadence / threshold / threshold type) on
   the ten achievements whose criteria map exactly to a metric supported by
   the award engine (``posts``, ``qs``).

Four legacy achievements are intentionally left as manual (``auto_award =
false``) because they cannot be expressed with the engine's current
metrics:

* The Priest / The Monk -- scoped to QSource events. The engine ignores
  event-type/-tag filters (only first/second/third-F category filters are
  applied), so QSource cannot be isolated for auto-award yet.
* Cadre -- "Q at 7 different AOs in a month". The ``unique_aos`` metric
  counts distinct AOs *posted at*, not *Q'd at*.
* Holding Down the Fort -- "50 posts at a single AO". ``posts_at_ao`` needs
  a specific ``ao_org_id`` filter and has no "max over any one AO" mode.

These remain available as named achievements that admins can tag manually.

Note on fidelity: WeaselBot counted "beatdown" posts/Qs only (excluding
QSource and ruck). Because the engine cannot filter those out by type, the
auto-award achievements seeded here count all posts/Qs (``auto_filters``
empty). Regions wanting stricter criteria can create custom achievements.

Revision ID: c4f7a1e92b30
Revises: f676d53e006c
Create Date: 2026-06-08 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4f7a1e92b30"
down_revision: Union[str, None] = "f676d53e006c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Canonical legacy WeaselBot achievements. ``auto`` rows carry the
# (threshold_type, threshold, cadence) that the award engine understands;
# ``auto = None`` rows are seeded as manual-only (named) achievements.
ACHIEVEMENTS = [
    # name, description, auto
    ("The Priest", "Post for 25 Q Source lessons in a year", None),
    ("The Monk", "Post at 4 Q Sources in a month", None),
    ("Leader of Men", "Q at 4 beatdowns in a month", ("qs", 4, "monthly")),
    ("The Boss", "Q at 6 beatdowns in a month", ("qs", 6, "monthly")),
    ("Be the Hammer, Not the Nail", "Q at 6 beatdowns in a week", ("qs", 6, "weekly")),
    ("Cadre", "Q at 7 different AOs in a month", None),
    ("El Presidente", "Q at 20 beatdowns in a year", ("qs", 20, "yearly")),
    ("El Quatro", "Post at 25 beatdowns in a year", ("posts", 25, "yearly")),
    ("Golden Boy", "Post at 50 beatdowns in a year", ("posts", 50, "yearly")),
    ("Centurion", "Post at 100 beatdowns in a year", ("posts", 100, "yearly")),
    ("Karate Kid", "Post at 150 beatdowns in a year", ("posts", 150, "yearly")),
    ("Crazy Person", "Post at 200 beatdowns in a year", ("posts", 200, "yearly")),
    ("6 Pack", "Post at 6 beatdowns in a week", ("posts", 6, "weekly")),
    ("Holding Down the Fort", "Post 50 times at an AO", None),
]

# Legacy codes from WeaselBot's achievement_tables.py, preserved in ``meta``
# so the named achievements stay traceable to their origin.
LEGACY_CODES = {
    "The Priest": "the_priest",
    "The Monk": "the_monk",
    "Leader of Men": "leader_of_men",
    "The Boss": "the_boss",
    "Be the Hammer, Not the Nail": "be_the_hammer_not_the_nail",
    "Cadre": "cadre",
    "El Presidente": "el_presidente",
    "El Quatro": "el_quatro",
    "Golden Boy": "golden_boy",
    "Centurion": "centurion",
    "Karate Kid": "karate_kid",
    "Crazy Person": "crazy_person",
    "6 Pack": "6_pack",
    "Holding Down the Fort": "holding_down_the_fort",
}


def upgrade() -> None:
    bind = op.get_bind()
    existing = {row[0] for row in bind.execute(sa.text("SELECT name FROM achievements")).fetchall()}

    for name, description, auto in ACHIEVEMENTS:
        meta = f'{{"source": "weaselbot", "legacy_code": "{LEGACY_CODES[name]}"}}'
        if name not in existing:
            if auto:
                threshold_type, threshold, cadence = auto
                bind.execute(
                    sa.text(
                        """
                        INSERT INTO achievements
                            (name, description, specific_org_id, is_active, auto_award,
                             auto_cadence, auto_threshold, auto_threshold_type, auto_filters, meta)
                        VALUES
                            (:name, :description, NULL, true, true,
                             CAST(:cadence AS achievement_cadence), :threshold, :threshold_type,
                             CAST('{}' AS json), CAST(:meta AS json))
                        """
                    ),
                    {
                        "name": name,
                        "description": description,
                        "cadence": cadence,
                        "threshold": threshold,
                        "threshold_type": threshold_type,
                        "meta": meta,
                    },
                )
            else:
                bind.execute(
                    sa.text(
                        """
                        INSERT INTO achievements
                            (name, description, specific_org_id, is_active, auto_award, meta)
                        VALUES
                            (:name, :description, NULL, true, false, CAST(:meta AS json))
                        """
                    ),
                    {"name": name, "description": description, "meta": meta},
                )
        else:
            # Already seeded by name (the baseline seed predates the auto-award
            # columns and meta). Backfill the legacy_code into meta if absent,
            # and turn on auto-award when the achievement maps to a metric.
            bind.execute(
                sa.text("UPDATE achievements SET meta = COALESCE(meta, CAST(:meta AS json)) WHERE name = :name"),
                {"name": name, "meta": meta},
            )
            if auto:
                threshold_type, threshold, cadence = auto
                bind.execute(
                    sa.text(
                        """
                        UPDATE achievements
                           SET auto_award = true,
                               auto_cadence = CAST(:cadence AS achievement_cadence),
                               auto_threshold = :threshold,
                               auto_threshold_type = :threshold_type,
                               description = :description
                         WHERE name = :name
                        """
                    ),
                    {
                        "name": name,
                        "description": description,
                        "cadence": cadence,
                        "threshold": threshold,
                        "threshold_type": threshold_type,
                    },
                )


def downgrade() -> None:
    bind = op.get_bind()

    # Names this migration inserted (everything except the three from the
    # baseline seed) are removed; their award rows go first to satisfy FKs.
    baseline = {"The Priest", "The Monk", "Leader of Men"}
    inserted = [name for name, _, _ in ACHIEVEMENTS if name not in baseline]
    bind.execute(
        sa.text(
            "DELETE FROM achievements_x_users WHERE achievement_id IN "
            "(SELECT id FROM achievements WHERE name = ANY(:names))"
        ),
        {"names": inserted},
    )
    bind.execute(sa.text("DELETE FROM achievements WHERE name = ANY(:names)"), {"names": inserted})

    # Revert the auto-award config applied to the baseline-seeded achievement.
    bind.execute(
        sa.text(
            """
            UPDATE achievements
               SET auto_award = false,
                   auto_cadence = NULL,
                   auto_threshold = NULL,
                   auto_threshold_type = NULL
             WHERE name = 'Leader of Men'
            """
        )
    )
