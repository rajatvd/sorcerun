import click
import subprocess
from pymongo import MongoClient
import os
import json
import yaml
import contextlib


@contextlib.contextmanager
def mongodb_server(db_path, conf_path):
    if not os.path.exists(db_path):
        os.makedirs(db_path)

    mongodb_process = subprocess.Popen(
        ["mongod", "--config", conf_path],
        stdout=subprocess.DEVNULL,  # Suppress output
    )

    try:
        yield
    finally:
        print("Terimnating mongod server...")
        mongodb_process.terminate()
        mongodb_process.wait()


def create_mongod_conf(db_path, conf_path, auth=True):
    conf_data = {
        "storage": {
            "dbPath": db_path,
        },
        "net": {
            "bindIp": "127.0.0.1",
            "port": 27017,
        },
        "security": {
            "authorization": "enabled" if auth else "disabled",
        },
        "systemLog": {
            "destination": "file",
            "path": os.path.join(db_path, "mongod.log"),
            "logAppend": True,
        },
    }

    with open(conf_path, "w") as conf_file:
        yaml.dump(conf_data, conf_file, default_flow_style=False)


def init_mongodb(db_path, db_name, username, password):
    db_path = os.path.abspath(db_path)
    if not os.path.exists(db_path):
        os.makedirs(db_path)

    # --- create admin user with no auth ---
    conf_path_noauth = os.path.join(db_path, "mongod_noauth.conf")
    create_mongod_conf(db_path, conf_path_noauth, auth=False)

    with mongodb_server(db_path, conf_path_noauth):
        client = MongoClient("localhost", 27017)
        db = client["admin"]
        db.command("ping")
        client.admin.command(
            "createUser",
            "admin",
            pwd="admin",
            roles=[{"role": "userAdminAnyDatabase", "db": "admin"}],
        )

    # --- create specific user with auth for database ---
    conf_path = os.path.join(db_path, "mongod.conf")
    create_mongod_conf(db_path, conf_path)


@click.group()
def sorcerun():
    pass


@sorcerun.group()
def mongo():
    pass


@mongo.command()
def init():
    click.echo("Initializing a new MongoDB database locally...")

    # 1. Ask for path to store MongoDB data
    db_path = click.prompt(
        "Please enter the path where you'd like to store the MongoDB database files"
    )

    with mongodb_server(db_path, conf_path):
        # 3. Ask the user for a database name
        db_name = click.prompt("Please enter a name for the new MongoDB database")

        # 4. Create a database in the above server using pymongo
        click.echo(f"Creating a new MongoDB database named {db_name}...")
        client = MongoClient("mongodb://admin:admin@localhost:27017/?authSource=admin")

        db = client[db_name]
        db.command("ping")

        click.echo(client.list_database_names())

        click.echo(f"MongoDB database {db_name} has been created at {db_path}.")

        # 6. Ask the user for a new username and password
        username = click.prompt("Please enter a new username for the MongoDB database")
        password = click.prompt(
            "Please enter a new password for the MongoDB database", hide_input=True
        )

        # 7. Create a new user with access to the database
        click.echo(f"Creating a new user for the {db_name} database...")
        client.admin.command(
            "createUser",
            username,
            pwd=password,
            roles=[{"role": "readWrite", "db": db_name}],
        )

        # 8. Create auth.json file
        auth_data = {
            "client_kwargs": {
                "host": "localhost",
                "port": 27017,
                "username": username,
                "password": password,
                "authSource": "admin",
            },
            "db_name": db_name,
        }

        with open("auth.json", "w") as auth_file:
            json.dump(auth_data, auth_file, indent=4)

        click.echo("Auth.json file has been created with the provided credentials.")


if __name__ == "__main__":
    sorcerun()
