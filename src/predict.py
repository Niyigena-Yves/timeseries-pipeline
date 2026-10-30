"""Fetch country history from the API and score the latest model-ready year."""

import argparse
import json
import os
from pathlib import Path
from typing import Any, Optional, Union
from urllib.parse import urlencode
from urllib.request import urlopen

import joblib

from src.preprocessing import FEATURES, prepare_features

DEFAULT_MODEL = Path(__file__).resolve().parents[1] / "models" / "crisis_model.joblib"


def predict(records: list[dict[str, Any]], model_path: Optional[Union[str, Path]] = None) -> list[dict[str, Any]]:
	"""Score the latest feature-complete record for each country in the input."""
	artifact_path = Path(model_path or os.getenv("MODEL_PATH", DEFAULT_MODEL))
	if not artifact_path.is_file():
		raise FileNotFoundError(
			f"Model artifact not found at {artifact_path}. Run the modeling notebook to create it."
		)

	artifact = joblib.load(artifact_path)
	model = artifact["model"]
	features = artifact.get("features", FEATURES)
	feature_frame = prepare_features(records)
	if feature_frame.empty:
		raise ValueError("Not enough consecutive history to create lag and moving-average features")
	missing_features = sorted(set(features).difference(feature_frame.columns))
	if missing_features:
		raise ValueError(f"Model features are unavailable: {', '.join(missing_features)}")

	predictions: list[dict[str, Any]] = []
	for _, row in feature_frame.groupby("country", sort=False).tail(1).iterrows():
		input_frame = row.loc[list(features)].to_frame().T
		predicted = int(model.predict(input_frame)[0])
		probability = None
		if hasattr(model, "predict_proba"):
			class_labels = list(model.classes_)
			probabilities = model.predict_proba(input_frame)[0]
			probability = float(probabilities[class_labels.index(1)]) if 1 in class_labels else 0.0
		predictions.append(
			{
				"cc3": row.get("cc3"),
				"country": row["country"],
				"year": int(row["year"]),
				"prediction": predicted,
				"label": "crisis" if predicted else "no_crisis",
				"probability": probability,
			}
		)
	return predictions


def fetch_records(
	api_url: str,
	store: str,
	country_code: str,
	start_year: Optional[int] = None,
	end_year: Optional[int] = None,
) -> list[dict[str, Any]]:
	params: dict[str, str | int] = {"cc3": country_code.upper()}
	if start_year is not None:
		params["start_year"] = start_year
	if end_year is not None:
		params["end_year"] = end_year
	endpoint = f"{api_url.rstrip('/')}/{store}/records?{urlencode(params)}"
	with urlopen(endpoint, timeout=15) as response:
		records = json.loads(response.read().decode("utf-8"))
	if not records:
		raise ValueError(f"No records returned from {endpoint}")
	return records


def main() -> None:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--api-url", default="http://127.0.0.1:8000")
	parser.add_argument("--store", choices=("sql", "mongo"), default="sql")
	parser.add_argument("--country-code", required=True, help="ISO alpha-3 country code, e.g. ZWE")
	parser.add_argument("--start-year", type=int)
	parser.add_argument("--end-year", type=int)
	parser.add_argument("--model-path", type=Path, default=DEFAULT_MODEL)
	args = parser.parse_args()

	records = fetch_records(
		args.api_url,
		args.store,
		args.country_code,
		args.start_year,
		args.end_year,
	)
	print(json.dumps(predict(records, args.model_path), indent=2))


if __name__ == "__main__":
	main()
