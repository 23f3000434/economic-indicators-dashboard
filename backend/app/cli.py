import argparse
import asyncio
import getpass
import json
import time

from .auth import Auth
from .config import Settings
from .db import Database
from .gdp import Collector, read_panel


def main():
    parser = argparse.ArgumentParser(
        description="Private local database administration; no default credentials"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("migrate")
    user = commands.add_parser("create-user")
    user.add_argument("username")
    commands.add_parser("collect-gdp")
    commands.add_parser("read-gdp")
    args = parser.parse_args()
    settings = Settings.load()
    database = Database(settings.database)
    database.migrate()
    if args.command == "create-user":
        password = getpass.getpass("Password (12+ characters): ")
        if password != getpass.getpass("Confirm password: "):
            parser.error("Passwords do not match")
        Auth(settings, database, time.time).create_user(args.username, password)
        print("User created. Share evaluation credentials separately.")
    elif args.command == "collect-gdp":
        if not asyncio.run(Collector(settings, database, time.time).collect_once()):
            raise SystemExit(
                "Collection did not succeed; inspect collection state, retained data is unchanged."
            )
        print("GDP collection succeeded.")
    elif args.command == "read-gdp":
        print(json.dumps(read_panel(database, settings, time.time()).model_dump(), indent=2))
    else:
        print("Migrations applied.")


if __name__ == "__main__":
    main()
