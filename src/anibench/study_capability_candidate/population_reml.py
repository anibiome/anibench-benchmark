# SPDX-FileCopyrightText: 2026 ANI
# SPDX-License-Identifier: Apache-2.0
"""Exact Gaussian restricted-quadratic covariance, fixed biological mean strata.
No public promotion. Validate against explicit dense P before integration.
"""

import numpy as np

from . import compiler as c


def psd_inverse(A):
    A = (A + A.T) / 2
    d, U = np.linalg.eigh(A)
    tol = 1e-10 * max(1.0, float(d[-1]) if len(d) else 1.0)
    if len(d) and d[0] < -tol:
        raise ValueError("nuisance Gram notPSD")
    use = d > tol
    return (U[:, use] / d[use]) @ U[:, use].T, int(use.sum())


def derivatives(panel, H):
    m = len(panel["coordinates"])
    pairs = [(i, j) for i in range(m) for j in range(i, m)]
    out = []
    for i, j in pairs:
        E = np.zeros((3 * m, 3 * m))
        E[3 * i, 3 * j] = E[3 * j, 3 * i] = 1.0
        out.append(H @ E @ H.T)
    return out


def information(panel, groups, q):
    """Aggregate exact trace formulas, O(patterns), never allocate people×people."""
    m = len(panel["coordinates"])
    k = m * (m + 1) // 2
    total = np.zeros((k, k))
    strata = {}
    diagnostics = []
    for g in groups:
        strata.setdefault((g["site"], g["arm"], g["modifier"]), []).append(g)
    for gs in strata.values():
        G = np.zeros((3 * m, 3 * m))
        A = np.zeros((k, 3 * m, 3 * m))
        Bcross = np.zeros((k, k, 3 * m, 3 * m))
        base = np.zeros((k, k))
        nobs = 0
        retained_rows = 0
        persons = 0
        for g in gs:
            H, R, B, events = c.event_model(panel, g, q)
            if not events:
                continue
            n = g["n"]
            persons += n
            nobs += n * len({e["physical_id"] for e in g["events"]})
            retained_rows += n * len(events)
            V = H @ B @ H.T + R
            W = np.linalg.inv(V)
            D = derivatives(panel, H)
            U = W @ H
            G += n * H.T @ U
            for a in range(k):
                A[a] += n * U.T @ D[a] @ U
                for b in range(k):
                    base[a, b] += n * np.trace(W @ D[a] @ W @ D[b])
                    Bcross[a, b] += n * U.T @ D[a] @ W @ D[b] @ U
        M, rank = psd_inverse(G)
        I = np.empty((k, k))
        for a in range(k):
            for b in range(k):
                I[a, b] = 0.5 * (
                    base[a, b]
                    - np.trace(M @ (Bcross[a, b] + Bcross[b, a]))
                    + np.trace(M @ A[a] @ M @ A[b])
                )
        I = (I + I.T) / 2
        tol = 1e-9 * max(1.0, np.linalg.norm(base, 2))
        if np.linalg.eigvalsh(I)[0] < -tol:
            raise ValueError("negative restricted quadratic information")
        # Only cancellation-scale entries are zeroed; never add ridge or certify an ambiguous rank.
        I[np.abs(I) < tol * 1e-3] = 0.0
        total += I
        diagnostics.append(
            {
                "people": persons,
                "observations": nobs,
                "retained_target_rows": retained_rows,
                "mean_rank": rank,
            }
        )
    return (total + total.T) / 2, diagnostics


def dense_oracle(panel, groups, q):
    """Independent small explicit block construction for audit, never real cohorts."""
    m = len(panel["coordinates"])
    stratakeys = list(dict.fromkeys((g["site"], g["arm"], g["modifier"]) for g in groups))
    blocks = []
    for g in groups:
        H, R, B, _events = c.event_model(panel, g, q)
        for _ in range(g["n"]):
            blocks.append(
                (
                    H @ B @ H.T + R,
                    H,
                    derivatives(panel, H),
                    stratakeys.index((g["site"], g["arm"], g["modifier"])),
                )
            )
    n = sum(len(V) for V, _, _, _ in blocks)
    Vall = np.zeros((n, n))
    X = np.zeros((n, 3 * m * len(stratakeys)))
    Ds = [np.zeros((n, n)) for _ in range(m * (m + 1) // 2)]
    s = 0
    for V, H, der, k in blocks:
        t = s + len(V)
        Vall[s:t, s:t] = V
        X[s:t, k * 3 * m : (k + 1) * 3 * m] = H
        for i, D in enumerate(der):
            Ds[i][s:t, s:t] = D
        s = t
    W = np.linalg.inv(Vall)
    M = np.linalg.pinv(X.T @ W @ X, rcond=1e-10)
    P = W - W @ X @ M @ X.T @ W
    I = np.array([[0.5 * np.trace(P @ Da @ P @ Db) for Db in Ds] for Da in Ds])
    return I, {
        "PVp_equals_p": bool(np.allclose(P @ Vall @ P, P, rtol=1e-9, atol=1e-9)),
        "PX_zero": bool(np.allclose(P @ X, 0, atol=1e-9)),
    }
