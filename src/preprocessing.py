"""Preprocessing shared by model training, the API, and the forecast script."""

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
import pandas as pd

LAGS = (1, 2)
ROLL = 3
BASE_NUM = ("exch_usd", "inflation_log")
TARGET = "banking_crisis"
FEATURES = (
	[
		"systemic_crisis",
		"domestic_debt_in_default",
		"sovereign_external_debt_default",
		"gdp_weighted_default",
		"independence",
		"currency_crises",
		"inflation_crises",
		"exch_usd_log",
		"inflation_log",
		"inflation_change",
		"crisis_lag1",
	]
	+ [f"{column}_lag{lag}" for column in BASE_NUM for lag in LAGS]
	+ [f"{column}_ma{ROLL}" for column in BASE_NUM]
)


def flatten_record(record: Mapping[str, Any]) -> dict[str, Any]:
	"""Convert a MongoDB-shaped document to the flat source-data representation."""
	flattened = dict(record)
	economic = flattened.pop("economic", {})
	crisis = flattened.pop("crisis", {})
	flattened.update(economic)
	flattened.update(crisis)
	flattened.pop("_id", None)
	return flattened


def clean_records(records: Sequence[Mapping[str, Any]]) -> pd.DataFrame:
	if not records:
		raise ValueError("At least one country-year record is required")
	frame = pd.DataFrame([flatten_record(record) for record in records])
	required = {
		"country",
		"year",
		"exch_usd",
		"inflation_annual_cpi",
		"gdp_weighted_default",
		"banking_crisis",
		"systemic_crisis",
		"domestic_debt_in_default",
		"sovereign_external_debt_default",
		"independence",
		"currency_crises",
		"inflation_crises",
	}
	missing = sorted(required.difference(frame.columns))
	if missing:
		raise ValueError(f"Records are missing required fields: {', '.join(missing)}")

	frame["year"] = pd.to_numeric(frame["year"], errors="raise").astype(int)
	frame["banking_crisis"] = frame["banking_crisis"].map(
		lambda value: int(value == "crisis") if isinstance(value, str) else int(value)
	)
	frame["currency_crises"] = pd.to_numeric(frame["currency_crises"], errors="raise").clip(upper=1)
	frame["inflation_log"] = np.sign(frame["inflation_annual_cpi"]) * np.log1p(
		np.abs(frame["inflation_annual_cpi"])
	)
	frame["exch_usd_log"] = np.log1p(frame["exch_usd"])
	return frame.sort_values(["country", "year"]).reset_index(drop=True)


def add_time_features(frame: pd.DataFrame) -> pd.DataFrame:
	"""Build past-only features without bridging missing calendar years."""
	output = []
	for country, group in frame.groupby("country", sort=False):
		group = group.drop_duplicates("year", keep="last").set_index("year").sort_index()
		full = group.reindex(range(int(group.index.min()), int(group.index.max()) + 1))
		full["_observed"] = full["country"].notna()
		full["country"] = country
		for column in BASE_NUM:
			for lag in LAGS:
				full[f"{column}_lag{lag}"] = full[column].shift(lag)
			full[f"{column}_ma{ROLL}"] = full[column].shift(1).rolling(ROLL, min_periods=ROLL).mean()
		full["inflation_change"] = full["inflation_log"] - full["inflation_log_lag1"]
		full["crisis_lag1"] = full[TARGET].shift(1)
		output.append(
			full.loc[full["_observed"]]
			.drop(columns="_observed")
			.rename_axis("year")
			.reset_index()
		)
	if not output:
		return pd.DataFrame(columns=list(frame.columns) + FEATURES)
	return pd.concat(output, ignore_index=True).sort_values(["country", "year"]).reset_index(drop=True)


def prepare_features(records: Sequence[Mapping[str, Any]]) -> pd.DataFrame:
	"""Return model-ready country-years with sufficient prior history."""
	engineered = add_time_features(clean_records(records))
	available = [column for column in FEATURES if column in engineered.columns]
	return engineered.dropna(subset=available).reset_index(drop=True)
