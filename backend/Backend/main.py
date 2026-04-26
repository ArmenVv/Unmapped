import json
import argparse
from src.agent import run_pipeline, run_employer_search


def main():
    parser = argparse.ArgumentParser(description="Job Suitability Agent")

    parser.add_argument(
        "--mode",
        choices=["candidate", "employer"],
        default="candidate",
        help="candidate = analyze and store a candidate, employer = search stored candidates",
    )

    parser.add_argument(
        "--job",
        type=str,
        help="Job description for candidate analysis",
    )

    parser.add_argument(
        "--query",
        type=str,
        help="Employer search query, for example: 'I need a React developer who knows CSS'",
    )

    parser.add_argument(
        "--data",
        type=str,
        default="data/conversations.json",
        help="Path to ChatGPT conversations export JSON",
    )

    parser.add_argument(
        "--results",
        type=int,
        default=5,
        help="Number of candidates to retrieve in employer mode",
    )

    args = parser.parse_args()

    if args.mode == "candidate":
        job = args.job or input("Enter the job you're looking for: ").strip()

        if not job:
            print("Error: job description cannot be empty.")
            return

        result = run_pipeline(job_description=job, data_path=args.data)

    else:
        query = args.query or input("Describe the employee you want to find: ").strip()

        if not query:
            print("Error: employer query cannot be empty.")
            return

        result = run_employer_search(employer_prompt=query, n_results=args.results)

    print("\n--- FINAL RESULT ---")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
