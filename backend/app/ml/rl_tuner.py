"""Self-improvement loop: nudge strategy parameters from realized rewards.

This is a deliberately simple stand-in for full RL — it implements an
exponential-average reward tracker and a coordinate-wise random-search
explorer. It runs after every closed paper trade and persists chosen
parameters to the DB. As trade history grows, this can be swapped for
a proper contextual-bandit or PPO trainer without changing the API.
"""
from __future__ import annotations

import json
import random
from dataclasses import asdict

from sqlalchemy.orm import Session

from ..db.models import LearningLog, StrategyParam
from ..strategy.ma_crossover import MACrossoverParams


PARAM_RANGES = {
    "fast": (10, 30),
    "slow": (40, 80),
    "rsi_floor": (25.0, 45.0),
    "rsi_ceiling": (65.0, 85.0),
    "atr_stop_mult": (1.0, 2.5),
    "atr_target_mult": (2.0, 5.0),
}
ALPHA = 0.2  # learning rate for the running-reward EMA
EXPLORE_PROB = 0.2


def load_params(session: Session, strategy: str = "ma_crossover") -> MACrossoverParams:
    row = session.get(StrategyParam, strategy)
    if row is None:
        params = MACrossoverParams()
        session.add(StrategyParam(strategy=strategy, params_json=json.dumps(asdict(params))))
        session.commit()
        return params
    return MACrossoverParams(**json.loads(row.params_json))


def record_reward(session: Session, strategy: str, reward: float) -> dict:
    """Update running reward and occasionally explore a new param set."""
    row = session.get(StrategyParam, strategy)
    if row is None:
        load_params(session, strategy)
        row = session.get(StrategyParam, strategy)

    n = row.n_updates + 1
    row.avg_reward = (1 - ALPHA) * row.avg_reward + ALPHA * reward
    row.n_updates = n
    changed = False
    if reward < 0 and random.random() < EXPLORE_PROB:
        params = MACrossoverParams(**json.loads(row.params_json))
        new_params = _perturb(params)
        row.params_json = json.dumps(asdict(new_params))
        changed = True
        session.add(LearningLog(
            kind="param_update",
            message=f"Negative reward {reward:.2f} → perturbed params to {asdict(new_params)}",
        ))
    session.commit()
    return {"avg_reward": row.avg_reward, "n_updates": n, "changed": changed}


def _perturb(p: MACrossoverParams) -> MACrossoverParams:
    field = random.choice(list(PARAM_RANGES.keys()))
    lo, hi = PARAM_RANGES[field]
    new_val = random.uniform(lo, hi) if isinstance(lo, float) else random.randint(lo, hi)
    d = asdict(p)
    d[field] = new_val
    # Keep fast<slow.
    if d["fast"] >= d["slow"]:
        d["slow"] = d["fast"] + 10
    return MACrossoverParams(**d)
