# import argparse
# import subprocess


# def run_ruff():
#     print("🔍 Running: ruff check --fix")
#     subprocess.run(["ruff", "check", "--fix"], check=True)

#     print("🧹 Running: ruff format")
#     subprocess.run(["ruff", "format"], check=True)

#     print("✅ Done!")


# def main():
#     parser = argparse.ArgumentParser(description="Sweepstake CLI")
#     subparsers = parser.add_subparsers(dest="command", required=True)

#     # Subcomando: ruff
#     ruff_parser = subparsers.add_parser("ruff", help="Run ruff check and format")

#     args = parser.parse_args()

#     if args.command == "ruff":
#         run_ruff()


# if __name__ == "__main__":
#     main()
