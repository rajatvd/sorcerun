import os
import yaml, json
import contextlib
import subprocess
import click
from pymongo import MongoClient
from .globals import AUTH_FILE, MONGOD_PORT, MONGOD_HOST


@contextlib.contextmanager
def mongodb_server(conf_path):
    click.echo(f"Starting MongoD server using config at {conf_path}")
    mongodb_process = subprocess.Popen(
        ["mongod", "--config", conf_path],
        stdout=subprocess.DEVNULL,  # Suppress output
    )

    # read from log file using tail and then clean it up using jq
    with open(conf_path, "r") as conf_file:
        conf = yaml.load(conf_file.read(), Loader=yaml.Loader)
        log_path = conf["systemLog"]["path"]

    # Failed attempt at reading important stuff from logs and printing on a line

    # separator = ", "
    # jq_command = (
    #     "["
    #     + separator.join(
    #         [
    #             '.t."$date"',
    #             r".s",
    #             r".c",
    #             r".id",
    #             r".ctx",
    #             r".msg",
    #             r".attr.mechanism",
    #             r".attr.principalName",
    #             r".attr.remote",
    #         ]
    #     )
    #     + "]"
    # )

    jq_command = "."
    taillog_process = subprocess.Popen(
        f"tail -f {log_path} | jq '{jq_command}'",
        shell=True,
    )
    try:
        yield
    finally:
        click.echo(f"Terimnating MongoD server that used config at {conf_path}\n")
        mongodb_process.terminate()
        mongodb_process.wait()

        taillog_process.terminate()
        taillog_process.wait()


def create_mongod_conf(db_path, conf_path, auth=True):
    conf_data = {
        "storage": {
            "dbPath": db_path,
        },
        "net": {
            "bindIp": MONGOD_HOST,
            "port": MONGOD_PORT,
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
        client = MongoClient(MONGOD_HOST, MONGOD_PORT)
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
        client = MongoClient(
            f"mongodb://admin:admin@{MONGOD_HOST}:{MONGOD_PORT}/?authSource=admin"
        )
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
                "host": MONGOD_HOST,
                "port": MONGOD_PORT,
                "username": username,
                "password": password,
                "authSource": "admin",
            },
            "db_name": db_name,
            "db_path": db_path,
            "conf_path": conf_path,
        }

        with open(AUTH_FILE, "w") as auth_file:
            json.dump(auth_data, auth_file, indent=4)
