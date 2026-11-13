"""
Phase 33: Multi-Armed Bandit (MAB) Reinforcement Learning Engine for Real-Time Dynamic Pricing & Offer Optimization.

Implements Bayesian Thompson Sampling, Upper Confidence Bound (UCB-1), Contextual Linear Bandits (Disjoint LinUCB),
and Epsilon-Greedy policies to maximize revenue-per-visitor while minimizing cumulative regret compared to static A/B testing.
"""

from __future__ import annotations

import copy
import math
import threading
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from scipy import stats


@dataclass
class BanditArm:
    """Represents a discrete dynamic pricing tier or promotional offer."""
    arm_id: str
    label: str
    price_multiplier: float
    true_conversion_rate: float
    base_unit_price: float = 1250.0

    # Bayesian Beta-Bernoulli Prior/Posterior parameters
    alpha: float = 1.0  # Success pseudo-counts (alpha >= 1)
    beta: float = 1.0   # Failure pseudo-counts (beta >= 1)

    # Lifetime Counters
    pull_count: int = 0
    conversion_count: int = 0
    total_revenue: float = 0.0

    # Contextual LinUCB Ridge Regression Parameters (Dimension d=4)
    # A_matrix = D^T D + I_d (Regularized Gram matrix)
    # b_vector = D^T c (Response vector)
    d: int = 4
    A_matrix: np.ndarray = field(default_factory=lambda: np.eye(4, dtype=np.float64))
    b_vector: np.ndarray = field(default_factory=lambda: np.zeros((4, 1), dtype=np.float64))

    @property
    def unit_price(self) -> float:
        return round(self.base_unit_price * self.price_multiplier, 2)

    @property
    def mean_conversion_rate(self) -> float:
        return self.alpha / (self.alpha + self.beta)

    @property
    def expected_revenue_per_visitor(self) -> float:
        return self.mean_conversion_rate * self.unit_price

    @property
    def true_expected_revenue(self) -> float:
        return self.true_conversion_rate * self.unit_price

    def credible_interval(self, confidence: float = 0.95) -> Tuple[float, float]:
        """Computes 95% Bayesian Credible Interval for conversion rate via Beta distribution quantiles."""
        lower_q = (1.0 - confidence) / 2.0
        upper_q = 1.0 - lower_q
        try:
            lo = float(stats.beta.ppf(lower_q, self.alpha, self.beta))
            hi = float(stats.beta.ppf(upper_q, self.alpha, self.beta))
            return round(max(0.0, lo), 4), round(min(1.0, hi), 4)
        except Exception:
            # Normal approximation fallback
            mean = self.mean_conversion_rate
            var = (self.alpha * self.beta) / (((self.alpha + self.beta) ** 2) * (self.alpha + self.beta + 1))
            std = math.sqrt(max(1e-6, var))
            z = 1.95996
            return round(max(0.0, mean - z * std), 4), round(min(1.0, mean + z * std), 4)

    def to_dict(self) -> Dict[str, Any]:
        lo, hi = self.credible_interval()
        return {
            "arm_id": self.arm_id,
            "label": self.label,
            "price_multiplier": self.price_multiplier,
            "unit_price_inr": self.unit_price,
            "pull_count": self.pull_count,
            "conversion_count": self.conversion_count,
            "total_revenue_inr": round(self.total_revenue, 2),
            "alpha": round(self.alpha, 2),
            "beta": round(self.beta, 2),
            "mean_conversion_rate": round(self.mean_conversion_rate, 4),
            "credible_interval_95": [lo, hi],
            "expected_revenue_per_visitor_inr": round(self.expected_revenue_per_visitor, 2),
            "true_conversion_rate": round(self.true_conversion_rate, 4),
            "true_expected_revenue_inr": round(self.true_expected_revenue, 2),
        }


DEFAULT_PRICING_ARMS: List[Dict[str, Any]] = [
    {
        "arm_id": "full_price",
        "label": "Standard Retail (0% Discount)",
        "price_multiplier": 1.00,
        "true_conversion_rate": 0.125,
    },
    {
        "arm_id": "promo_5",
        "label": "Dynamic 5% Promo Discount",
        "price_multiplier": 0.95,
        "true_conversion_rate": 0.158,
    },
    {
        "arm_id": "volume_10",
        "label": "Volume 10% Bundle Discount",
        "price_multiplier": 0.90,
        "true_conversion_rate": 0.205,
    },
    {
        "arm_id": "clearance_15",
        "label": "Flash 15% Clearance Deal",
        "price_multiplier": 0.85,
        "true_conversion_rate": 0.228,
    },
    {
        "arm_id": "premium_addon",
        "label": "Value-Add Gift Bundle (+8% Price)",
        "price_multiplier": 1.08,
        "true_conversion_rate": 0.142,
    },
]


class MultiArmedBanditEngine:
    """
    Enterprise Multi-Armed Bandit Reinforcement Learning Engine for Dynamic Pricing.
    Supports Thompson Sampling, UCB-1, Disjoint Contextual LinUCB, and Epsilon-Greedy.
    """

    def __init__(
        self,
        base_unit_price: float = 1250.0,
        arms_spec: Optional[List[Dict[str, Any]]] = None,
        seed: Optional[int] = 42,
    ) -> None:
        self.base_unit_price = base_unit_price
        self.lock = threading.Lock()
        self.rng = np.random.default_rng(seed)
        self.total_rounds = 0
        self.total_revenue = 0.0
        self.total_conversions = 0

        specs = arms_spec or DEFAULT_PRICING_ARMS
        self.arms: Dict[str, BanditArm] = {}
        for s in specs:
            arm = BanditArm(
                arm_id=s["arm_id"],
                label=s["label"],
                price_multiplier=float(s["price_multiplier"]),
                true_conversion_rate=float(s.get("true_conversion_rate", 0.15)),
                base_unit_price=self.base_unit_price,
            )
            self.arms[arm.arm_id] = arm

    def reset(self, seed: Optional[int] = None) -> None:
        """Resets bandit history and resets Bayesian priors to uninformative state."""
        with self.lock:
            if seed is not None:
                self.rng = np.random.default_rng(seed)
            self.total_rounds = 0
            self.total_revenue = 0.0
            self.total_conversions = 0
            for arm in self.arms.values():
                arm.alpha = 1.0
                arm.beta = 1.0
                arm.pull_count = 0
                arm.conversion_count = 0
                arm.total_revenue = 0.0
                arm.A_matrix = np.eye(arm.d, dtype=np.float64)
                arm.b_vector = np.zeros((arm.d, 1), dtype=np.float64)

    def get_arms(self) -> List[Dict[str, Any]]:
        """Returns snapshot of all arms with current empirical and posterior statistics."""
        with self.lock:
            res = [arm.to_dict() for arm in self.arms.values()]
            tot_pulls = max(1, sum(a["pull_count"] for a in res))
            for a in res:
                a["pull_share_pct"] = round((a["pull_count"] / tot_pulls) * 100.0, 2)
            return res

    def select_arm(
        self,
        strategy: str = "thompson",
        context: Optional[List[float]] = None,
        exploration_factor: float = 1.0,
    ) -> Dict[str, Any]:
        """
        Selects optimal pricing arm based on selected reinforcement learning strategy.
        Strategies:
          - 'thompson': Bayesian Thompson Sampling on expected revenue (Beta posterior sampling * price)
          - 'ucb1': Upper Confidence Bound on conversion rate * price
          - 'linucb': Contextual Disjoint Linear UCB given customer context vector
          - 'epsilon_greedy': Epsilon exploration with harmonic decay
        """
        strat = strategy.lower().strip()
        with self.lock:
            arm_keys = list(self.arms.keys())
            if not arm_keys:
                raise ValueError("No bandit arms configured.")

            # Default customer context: [1.0 (intercept), recency_norm, log_spend_norm, cart_size_norm]
            x_vec = np.array(context or [1.0, 0.45, 0.65, 0.30], dtype=np.float64).reshape(-1, 1)
            if x_vec.shape[0] < 4:
                pad = np.zeros((4 - x_vec.shape[0], 1), dtype=np.float64)
                x_vec = np.vstack([x_vec, pad])
            elif x_vec.shape[0] > 4:
                x_vec = x_vec[:4]

            chosen_arm_id = arm_keys[0]
            score_map: Dict[str, float] = {}
            is_exploration = False
            reason = ""

            if strat == "thompson":
                # Sample expected revenue from Beta posterior: theta_k ~ Beta(alpha_k, beta_k) * price_k
                best_sampled_rev = -1.0
                for k in arm_keys:
                    arm = self.arms[k]
                    # Direct numpy beta sampling
                    sampled_rate = float(self.rng.beta(arm.alpha, arm.beta))
                    sampled_rev = sampled_rate * arm.unit_price
                    score_map[k] = round(sampled_rev, 2)
                    if sampled_rev > best_sampled_rev:
                        best_sampled_rev = sampled_rev
                        chosen_arm_id = k

                # Check if this choice deviates from the current empirical mean
                empirical_best = max(arm_keys, key=lambda k: self.arms[k].expected_revenue_per_visitor)
                is_exploration = bool(chosen_arm_id != empirical_best)
                reason = f"Thompson Sampling drawn posterior revenue: ₹{best_sampled_rev:.2f}/visitor"

            elif strat == "ucb1":
                # UCB-1: If any arm unpulled, explore it first
                unpulled = [k for k in arm_keys if self.arms[k].pull_count == 0]
                if unpulled:
                    chosen_arm_id = unpulled[0]
                    is_exploration = True
                    reason = f"UCB-1 mandatory initialization (arm {chosen_arm_id} unpulled)"
                    for k in arm_keys:
                        score_map[k] = float("inf") if self.arms[k].pull_count == 0 else self.arms[k].expected_revenue_per_visitor
                else:
                    t = max(1, self.total_rounds)
                    best_ucb = -1.0
                    for k in arm_keys:
                        arm = self.arms[k]
                        mu = arm.mean_conversion_rate
                        # Standard UCB-1 bonus
                        bonus = exploration_factor * math.sqrt((2.0 * math.log(t)) / arm.pull_count)
                        ucb_rate = min(1.0, mu + bonus)
                        ucb_rev = ucb_rate * arm.unit_price
                        score_map[k] = round(ucb_rev, 2)
                        if ucb_rev > best_ucb:
                            best_ucb = ucb_rev
                            chosen_arm_id = k
                    empirical_best = max(arm_keys, key=lambda k: self.arms[k].expected_revenue_per_visitor)
                    is_exploration = bool(chosen_arm_id != empirical_best)
                    reason = f"UCB-1 optimistic expected revenue bound: ₹{best_ucb:.2f}/visitor"

            elif strat == "linucb":
                # Disjoint LinUCB: theta_k = A_k^{-1} b_k, p_k = theta_k^T x + alpha * sqrt(x^T A_k^{-1} x)
                best_lin_score = -1e9
                for k in arm_keys:
                    arm = self.arms[k]
                    A_inv = np.linalg.pinv(arm.A_matrix)
                    theta = A_inv @ arm.b_vector
                    ridge_est = float((theta.T @ x_vec).item())
                    # Exploration variance width
                    variance_width = float(np.sqrt(max(1e-9, (x_vec.T @ A_inv @ x_vec).item())))
                    score = (ridge_est + exploration_factor * variance_width) * arm.unit_price
                    score_map[k] = round(score, 2)
                    if score > best_lin_score:
                        best_lin_score = score
                        chosen_arm_id = k
                empirical_best = max(arm_keys, key=lambda k: self.arms[k].expected_revenue_per_visitor)
                is_exploration = bool(chosen_arm_id != empirical_best)
                reason = f"Contextual LinUCB score: ₹{best_lin_score:.2f} (Context: RFM={float(x_vec[1,0]):.2f}, Spend={float(x_vec[2,0]):.2f})"

            elif strat == "epsilon_greedy":
                t = max(1, self.total_rounds)
                epsilon = max(0.05, exploration_factor / math.sqrt(t))
                if float(self.rng.random()) < epsilon:
                    chosen_arm_id = str(self.rng.choice(arm_keys))
                    is_exploration = True
                    reason = f"Epsilon-Greedy random exploration (ε = {epsilon:.3f})"
                else:
                    chosen_arm_id = max(arm_keys, key=lambda k: self.arms[k].expected_revenue_per_visitor)
                    is_exploration = False
                    reason = f"Epsilon-Greedy exploitation of best empirical arm (ε = {epsilon:.3f})"
                for k in arm_keys:
                    score_map[k] = round(self.arms[k].expected_revenue_per_visitor, 2)
            else:
                raise ValueError(f"Unknown bandit strategy '{strategy}'. Supported: thompson, ucb1, linucb, epsilon_greedy")

            chosen_arm = self.arms[chosen_arm_id]
            return {
                "selected_arm_id": chosen_arm.arm_id,
                "arm_label": chosen_arm.label,
                "price_multiplier": chosen_arm.price_multiplier,
                "offered_price_inr": chosen_arm.unit_price,
                "strategy_used": strat,
                "is_exploration": is_exploration,
                "decision_reason": reason,
                "scores_by_arm": score_map,
                "estimated_conversion_rate": round(chosen_arm.mean_conversion_rate, 4),
                "expected_revenue_inr": round(chosen_arm.expected_revenue_per_visitor, 2),
                "customer_context": [round(float(v), 3) for v in x_vec.flatten()],
            }

    def record_reward(
        self,
        arm_id: str,
        converted: bool,
        revenue: Optional[float] = None,
        context: Optional[List[float]] = None,
    ) -> Dict[str, Any]:
        """
        Observes real customer purchase feedback, updates Beta posteriors and LinUCB Gram matrices.
        """
        with self.lock:
            if arm_id not in self.arms:
                raise ValueError(f"Arm '{arm_id}' not found.")
            arm = self.arms[arm_id]

            # Update base counters
            arm.pull_count += 1
            self.total_rounds += 1

            rev = float(revenue if revenue is not None else (arm.unit_price if converted else 0.0))
            if converted:
                arm.conversion_count += 1
                arm.total_revenue += rev
                arm.alpha += 1.0
                self.total_conversions += 1
                self.total_revenue += rev
            else:
                arm.beta += 1.0

            # Update Contextual LinUCB Gram matrix
            x_vec = np.array(context or [1.0, 0.45, 0.65, 0.30], dtype=np.float64).reshape(-1, 1)
            if x_vec.shape[0] < 4:
                pad = np.zeros((4 - x_vec.shape[0], 1), dtype=np.float64)
                x_vec = np.vstack([x_vec, pad])
            elif x_vec.shape[0] > 4:
                x_vec = x_vec[:4]

            arm.A_matrix += x_vec @ x_vec.T
            reward_norm = 1.0 if converted else 0.0
            arm.b_vector += reward_norm * x_vec

            lo, hi = arm.credible_interval()
            return {
                "status": "success",
                "arm_id": arm.arm_id,
                "pull_count": arm.pull_count,
                "conversion_count": arm.conversion_count,
                "alpha": round(arm.alpha, 2),
                "beta": round(arm.beta, 2),
                "mean_conversion_rate": round(arm.mean_conversion_rate, 4),
                "credible_interval_95": [lo, hi],
                "expected_revenue_inr": round(arm.expected_revenue_per_visitor, 2),
                "total_arm_revenue_inr": round(arm.total_revenue, 2),
            }

    def get_performance(self) -> Dict[str, Any]:
        """Returns overall bandit performance and regret metrics compared to optimal Oracle."""
        with self.lock:
            arms_list = [arm.to_dict() for arm in self.arms.values()]
            tot_pulls = max(1, sum(a["pull_count"] for a in arms_list))
            for a in arms_list:
                a["pull_share_pct"] = round((a["pull_count"] / tot_pulls) * 100.0, 2)

            best_empirical_arm = max(arms_list, key=lambda a: a["expected_revenue_per_visitor_inr"])
            best_true_arm = max(arms_list, key=lambda a: a["true_expected_revenue_inr"])

            oracle_rev = best_true_arm["true_expected_revenue_inr"] * self.total_rounds
            actual_rev = self.total_revenue
            cumulative_regret = max(0.0, oracle_rev - actual_rev)

            return {
                "total_rounds": self.total_rounds,
                "total_conversions": self.total_conversions,
                "overall_conversion_rate": round(self.total_conversions / max(1, self.total_rounds), 4),
                "total_revenue_inr": round(self.total_revenue, 2),
                "best_empirical_arm": best_empirical_arm["arm_id"],
                "best_empirical_arm_label": best_empirical_arm["label"],
                "oracle_best_arm": best_true_arm["arm_id"],
                "oracle_expected_revenue_inr": round(oracle_rev, 2),
                "cumulative_regret_inr": round(cumulative_regret, 2),
                "regret_per_visitor_inr": round(cumulative_regret / max(1, self.total_rounds), 2),
                "arms": arms_list,
            }

    def simulate(
        self,
        rounds: int = 1000,
        strategy: str = "thompson",
        exploration_factor: float = 1.0,
        seed: Optional[int] = 42,
        custom_arms: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Runs full Monte-Carlo simulation comparing:
          1. Selected MAB Policy (Thompson / UCB-1 / LinUCB)
          2. Epsilon-Greedy Policy (decaying exploration)
          3. Traditional 50/50 A/B Test (70% exploration split equally, 30% exploitation)
          4. Full-Information Oracle (always picks optimal arm)
        Returns subsampled trajectories for interactive visual comparison and regret metrics.
        """
        rng = np.random.default_rng(seed)
        n_rounds = max(50, min(10000, int(rounds)))

        # Setup sandbox arms
        raw_specs = custom_arms or DEFAULT_PRICING_ARMS
        sim_arms_spec = [copy.deepcopy(s) for s in raw_specs]

        # Calculate Oracle arm based on true conversion * price
        best_arm_spec = max(
            sim_arms_spec,
            key=lambda s: s["true_conversion_rate"] * (self.base_unit_price * s["price_multiplier"]),
        )
        oracle_rate = best_arm_spec["true_conversion_rate"]
        oracle_price = self.base_unit_price * best_arm_spec["price_multiplier"]
        oracle_mean_rev = oracle_rate * oracle_price

        # Instantiate separate simulated agents
        mab_engine = MultiArmedBanditEngine(base_unit_price=self.base_unit_price, arms_spec=sim_arms_spec, seed=seed)
        egreedy_engine = MultiArmedBanditEngine(base_unit_price=self.base_unit_price, arms_spec=sim_arms_spec, seed=seed)

        # A/B Test state
        ab_phase_1_cutoff = int(0.70 * n_rounds)
        ab_pulls = {s["arm_id"]: 0 for s in sim_arms_spec}
        ab_conversions = {s["arm_id"]: 0 for s in sim_arms_spec}
        ab_revenue = {s["arm_id"]: 0.0 for s in sim_arms_spec}
        ab_winner_arm: Optional[str] = None

        # Cumulative tracking
        cum_rev_mab = 0.0
        cum_rev_egreedy = 0.0
        cum_rev_ab = 0.0
        cum_rev_oracle = 0.0

        # Subsample step collection for frontend charts (e.g. 50 data points)
        step_interval = max(1, n_rounds // 50)
        history: List[Dict[str, Any]] = []

        mab_arm_pulls = {s["arm_id"]: 0 for s in sim_arms_spec}

        for t in range(1, n_rounds + 1):
            # Shared customer context for this arrival
            rfm = float(rng.uniform(0.1, 0.9))
            spend = float(rng.uniform(0.1, 0.9))
            cart = float(rng.uniform(0.1, 0.8))
            ctx = [1.0, rfm, spend, cart]

            # 1. Oracle Choice
            is_oracle_conv = rng.random() < oracle_rate
            rev_oracle = oracle_price if is_oracle_conv else 0.0
            cum_rev_oracle += rev_oracle

            # 2. MAB Policy Choice
            mab_decision = mab_engine.select_arm(strategy=strategy, context=ctx, exploration_factor=exploration_factor)
            mab_arm_id = mab_decision["selected_arm_id"]
            mab_arm = mab_engine.arms[mab_arm_id]
            mab_arm_pulls[mab_arm_id] += 1

            is_mab_conv = rng.random() < mab_arm.true_conversion_rate
            rev_mab = mab_arm.unit_price if is_mab_conv else 0.0
            cum_rev_mab += rev_mab
            mab_engine.record_reward(mab_arm_id, is_mab_conv, rev_mab, context=ctx)

            # 3. Epsilon-Greedy Choice
            egreedy_decision = egreedy_engine.select_arm(strategy="epsilon_greedy", context=ctx, exploration_factor=exploration_factor)
            egreedy_arm_id = egreedy_decision["selected_arm_id"]
            egreedy_arm = egreedy_engine.arms[egreedy_arm_id]

            is_egreedy_conv = rng.random() < egreedy_arm.true_conversion_rate
            rev_egreedy = egreedy_arm.unit_price if is_egreedy_conv else 0.0
            cum_rev_egreedy += rev_egreedy
            egreedy_engine.record_reward(egreedy_arm_id, is_egreedy_conv, rev_egreedy, context=ctx)

            # 4. Traditional A/B Test Choice
            if t <= ab_phase_1_cutoff:
                # Equal split across all arms
                ab_arm_idx = (t - 1) % len(sim_arms_spec)
                ab_arm_spec = sim_arms_spec[ab_arm_idx]
                ab_arm_id = ab_arm_spec["arm_id"]
            else:
                if ab_winner_arm is None:
                    # Select winner based on phase 1 revenue per pull
                    ab_winner_arm = max(
                        sim_arms_spec,
                        key=lambda s: ab_revenue[s["arm_id"]] / max(1, ab_pulls[s["arm_id"]]),
                    )["arm_id"]
                ab_arm_id = ab_winner_arm
                ab_arm_spec = next(s for s in sim_arms_spec if s["arm_id"] == ab_arm_id)

            ab_unit_price = self.base_unit_price * ab_arm_spec["price_multiplier"]
            is_ab_conv = rng.random() < ab_arm_spec["true_conversion_rate"]
            rev_ab = ab_unit_price if is_ab_conv else 0.0
            cum_rev_ab += rev_ab
            ab_pulls[ab_arm_id] += 1
            if is_ab_conv:
                ab_conversions[ab_arm_id] += 1
                ab_revenue[ab_arm_id] += rev_ab

            # Record periodic trajectory step
            if t % step_interval == 0 or t == n_rounds:
                oracle_expected_so_far = oracle_mean_rev * t
                regret_mab = max(0.0, oracle_expected_so_far - cum_rev_mab)
                regret_ab = max(0.0, oracle_expected_so_far - cum_rev_ab)
                regret_egreedy = max(0.0, oracle_expected_so_far - cum_rev_egreedy)

                arm_shares = {
                    k: round((mab_arm_pulls[k] / t) * 100.0, 1)
                    for k in mab_arm_pulls
                }

                history.append({
                    "round": t,
                    "cumulative_revenue_mab": round(cum_rev_mab, 2),
                    "cumulative_revenue_ab": round(cum_rev_ab, 2),
                    "cumulative_revenue_egreedy": round(cum_rev_egreedy, 2),
                    "cumulative_revenue_oracle": round(cum_rev_oracle, 2),
                    "cumulative_regret_mab": round(regret_mab, 2),
                    "cumulative_regret_ab": round(regret_ab, 2),
                    "cumulative_regret_egreedy": round(regret_egreedy, 2),
                    "arm_allocation_shares": arm_shares,
                })

        # Calculate final executive comparison
        regret_mab_final = history[-1]["cumulative_regret_mab"]
        regret_ab_final = history[-1]["cumulative_regret_ab"]
        regret_saved_inr = max(0.0, regret_ab_final - regret_mab_final)
        regret_saved_pct = round((regret_saved_inr / max(1.0, regret_ab_final)) * 100.0, 1)
        revenue_gain_inr = round(cum_rev_mab - cum_rev_ab, 2)
        revenue_gain_pct = round((revenue_gain_inr / max(1.0, cum_rev_ab)) * 100.0, 2)

        # Identification check: did MAB allocate > 40% of pulls to the Oracle arm?
        oracle_pull_share = (mab_arm_pulls[best_arm_spec["arm_id"]] / n_rounds) * 100.0
        converged = bool(oracle_pull_share >= 40.0)

        return {
            "status": "completed",
            "rounds_simulated": n_rounds,
            "strategy": strategy,
            "base_unit_price_inr": self.base_unit_price,
            "oracle_best_arm": best_arm_spec["arm_id"],
            "oracle_best_label": best_arm_spec["label"],
            "oracle_true_conversion": best_arm_spec["true_conversion_rate"],
            "oracle_expected_revenue": round(oracle_mean_rev, 2),
            "total_revenue_mab_inr": round(cum_rev_mab, 2),
            "total_revenue_ab_inr": round(cum_rev_ab, 2),
            "total_revenue_oracle_inr": round(cum_rev_oracle, 2),
            "revenue_gain_vs_ab_inr": revenue_gain_inr,
            "revenue_gain_vs_ab_pct": revenue_gain_pct,
            "cumulative_regret_mab_inr": regret_mab_final,
            "cumulative_regret_ab_inr": regret_ab_final,
            "regret_saved_pct": regret_saved_pct,
            "converged_to_oracle": converged,
            "oracle_arm_pull_share_pct": round(oracle_pull_share, 1),
            "final_mab_arms": mab_engine.get_arms(),
            "trajectory": history,
        }


# Global singleton instance for live FastAPI backend
_BANDIT_ENGINE_SINGLETON: Optional[MultiArmedBanditEngine] = None


def get_bandit_engine() -> MultiArmedBanditEngine:
    global _BANDIT_ENGINE_SINGLETON
    if _BANDIT_ENGINE_SINGLETON is None:
        _BANDIT_ENGINE_SINGLETON = MultiArmedBanditEngine()
    return _BANDIT_ENGINE_SINGLETON
