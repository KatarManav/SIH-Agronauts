import argparse
import json

from app.ml.dataset import validate_training_csv


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate labeled landslide training data.")
    parser.add_argument("csv_path")
    args = parser.parse_args()
    report = validate_training_csv(args.csv_path)
    print(json.dumps(report.__dict__, indent=2))
    return 0 if report.ready_for_training else 1


if __name__ == "__main__":
    raise SystemExit(main())
