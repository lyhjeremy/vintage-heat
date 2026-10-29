"""Check the fixed-effects estimator in scripts/analyze.py against a plain
dummy-variable regression in statsmodels, on simulated data.
Run: python -m pytest tests/  (or python tests/test_estimator.py)"""
import pathlib, sys
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))
from analyze import fe_ols, lincomb  # noqa: E402


def simulate(seed=1, n=4000):
    rng = np.random.default_rng(seed)
    d = pd.DataFrame({"region": rng.integers(0, 30, n), "vintage": rng.integers(2000, 2017, n),
                      "taster": rng.integers(0, 8, n)})
    d["region"] = "r" + d.region.astype(str)
    d["taster"] = "t" + d.taster.astype(str)
    d["x1"] = rng.normal(size=n) + 0.3 * d.region.str[1:].astype(int) / 30
    d["x2"] = rng.normal(size=n)
    fe = d.region.str[1:].astype(int) * 0.1 + (d.vintage - 2000) * 0.05
    d["y"] = 1.5 * d.x1 - 0.7 * d.x2 + fe + rng.normal(size=n)
    d["w"] = rng.integers(1, 20, n)
    return d


def test_coefficients_and_ses_match_dummies():
    d = simulate()
    f = fe_ols(d, "y", ["x1", "x2"], ["region", "vintage", "taster"])
    r = smf.ols("y ~ x1 + x2 + C(region) + C(vintage) + C(taster)", d).fit(
        cov_type="cluster", cov_kwds={"groups": pd.factorize(d.region)[0]})
    for x in ("x1", "x2"):
        assert abs(f["coefs"][x]["b"] - r.params[x]) < 1e-8
        assert abs(f["coefs"][x]["se"] / r.bse[x] - 1) < 1e-6


def test_weighted_matches_wls():
    d = simulate(2)
    f = fe_ols(d, "y", ["x1", "x2"], ["region", "vintage"], w="w")
    r = smf.wls("y ~ x1 + x2 + C(region) + C(vintage)", d, weights=d.w).fit()
    for x in ("x1", "x2"):
        assert abs(f["coefs"][x]["b"] - r.params[x]) < 1e-8


def test_lincomb():
    d = simulate(3)
    f = fe_ols(d, "y", ["x1", "x2"], ["region", "vintage"])
    c = lincomb(f, {"x1": 1, "x2": -1})
    assert abs(c["b"] - (f["coefs"]["x1"]["b"] - f["coefs"]["x2"]["b"])) < 1e-12


if __name__ == "__main__":
    test_coefficients_and_ses_match_dummies(); test_weighted_matches_wls(); test_lincomb()
    print("3 tests passed")
