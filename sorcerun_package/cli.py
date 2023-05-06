import click
import subprocess
from pymongo import MongoClient
import os
import json
import yaml
import contextlib


@contextlib.contextmanager
def mongodb_server(conf_path):
    click.echo(f"Starting MongoD server using config at {conf_path}")
    mongodb_process = subprocess.Popen(
        ["mongod", "--config", conf_path],
        stdout=subprocess.DEVNULL,  # Suppress output
    )

    try:
        yield
    finally:
        click.echo(f"Terimnating MongoD server that used config at {conf_path}\n")
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

    with mongodb_server(conf_path_noauth):
        click.echo("Creating admin user in mongodb")
        client = MongoClient("localhost", 27017)
        db = client["admin"]
        db.command("ping")
        client.admin.command(
            "createUser",
            "admin",
            pwd="admin",
            roles=[{"role": "userAdminAnyDatabase", "db": "admin"}],
        )

    # remove the conf_file with no auth

    # --- create specific user with auth for database ---
    conf_path = os.path.join(db_path, "mongod.conf")
    create_mongod_conf(db_path, conf_path)

    with mongodb_server(conf_path):
        click.echo(f"Creating user {username} with access to database {db_name}")
        # client authed with as admin
        client = MongoClient("mongodb://admin:admin@localhost:27017/?authSource=admin")
        db = client[db_name]
        db.command("ping")

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
            "db_path": db_path,
            "conf_path": conf_path,
        }

        with open("auth.json", "w") as auth_file:
            json.dump(auth_data, auth_file, indent=4)


@click.group()
def sorcerun():
    pass


@sorcerun.group()
def mongo():
    pass


@mongo.command()
def init():
    db_path = click.prompt(
        "Please enter the path where you'd like to store the MongoDB database files"
    )
    db_name = click.prompt("Enter the name of the database to store runs")
    username = click.prompt("Please enter a new username for the MongoDB database")
    password = click.prompt(
        "Please enter a new password for the MongoDB database", hide_input=True
    )

    click.echo("\n")

    init_mongodb(
        db_path=db_path,
        db_name=db_name,
        username=username,
        password=password,
    )

    click.echo(
        "Initialization complete. Use `sorcerun mongo start` to start the configured mongodb server."
    )


@mongo.command()
def start():
    with open("auth.json", "r") as f:
        authjson = json.loads(f.read())
        conf_path = authjson["conf_path"]

    print(conf_path)
    with mongodb_server(conf_path):
        # TODO pipe log outputs to stdout or something nicely
        while True:
            pass


if __name__ == "__main__":
    sorcerun()
