import json
from sacred.commandline_options import CommandLineOption
from sacred.observers import MongoObserver
from pymongo import MongoClient


class AuthMongoDbOption(CommandLineOption):
    """Custom MongoObserver option with authentication.
    The authentication json file should contain two keys:
        'client_kwargs': directly passed to MongoClient
        'db_name': name of database to store runs (usually sacred)"""

    arg = "AUTH_FILE"
    short_flag = "M"
    arg_description = """Path to authentication json file."""

    @classmethod
    def apply(cls, args, run):
        with open(args) as f:
            auth = json.loads(f.read())
        atlas = auth.get("atlas_connection_string", 0)
        if atlas != 0:
            print(atlas)
            client = MongoClient(atlas)
        else:
            client = MongoClient(**auth["client_kwargs"])
        mongo = MongoObserver.create(db_name=auth["db_name"], client=client)
        run.observers.append(mongo)
