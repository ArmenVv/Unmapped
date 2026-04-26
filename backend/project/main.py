import json
import argparse
from src.agent import run_pipeline


def main():
    parser = argparse.ArgumentParser(description="Job Suitability Agent")
    parser.add_argument(
        "--job",
        type=str,
        help="Job description to analyze suitability for",
    )
    parser.add_argument(
        "--data",
        type=str,
        default="data/conversations.json",
        help="Path to ChatGPT conversations export JSON (default: data/conversations.json)",
    )
    args = parser.parse_args()

    job = args.job or input("Enter the job you're looking for: ").strip()

    if not job:
        print("Error: job description cannot be empty.")
        return

    result = run_pipeline(job_description=job, data_path=args.data)

    print("\n--- FINAL RESULT ---")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
