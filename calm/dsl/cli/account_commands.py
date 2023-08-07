import click
import json
import sys

from calm.dsl.api import get_api_client
from calm.dsl.config import get_context
from calm.dsl.log import get_logging_handle

from .main import get, delete, compile, describe, sync, create, verify
from .accounts import (
    create_account_from_dsl,
    compile_account_command,
    get_accounts,
    delete_account,
    describe_account,
    sync_account,
    verify_account,
    update_account_command,
)
from .main import get, delete, compile, describe, sync, create, update
from calm.dsl.log import get_logging_handle
from calm.dsl.api import get_api_client

LOG = get_logging_handle(__name__)


@get.command("accounts")
@click.option("--name", "-n", default=None, help="Search for provider account by name")
@click.option(
    "--filter", "filter_by", "-f", default=None, help="Filter projects by this string"
)
@click.option("--limit", "-l", default=20, help="Number of results to return")
@click.option(
    "--offset", "-s", default=0, help="Offset results by the specified amount"
)
@click.option(
    "--quiet", "-q", is_flag=True, default=False, help="Show only account names"
)
@click.option(
    "--all-items", "-a", is_flag=True, help="Get all items, including deleted ones"
)
@click.option(
    "--type",
    "account_type",
    default=None,
    multiple=True,
    help="Search for accounts of specific provider",
    type=click.Choice(
        ["aws", "k8s", "vmware", "azure", "gcp", "nutanix", "custom_provider"]
    ),
)
def _get_accounts(name, filter_by, limit, offset, quiet, all_items, account_type):
    """Get accounts, optionally filtered by a string"""

    get_accounts(name, filter_by, limit, offset, quiet, all_items, account_type)


@delete.command("account")
@click.argument("account_names", nargs=-1)
def _delete_account(account_names):
    """Deletes a account from settings"""

    delete_account(account_names)


@describe.command("account")
@click.argument("account_name")
def _describe_account(account_name):
    """Describe a account"""

    describe_account(account_name)


@sync.command("account", feature_min_version="3.0.0")
@click.argument("account_name")
def _sync_account(account_name):
    """Sync a platform account
    Args: account_name (string): name of the account to sync"""

    sync_account(account_name)


@verify.command("account", feature_min_version="3.0.0")
@click.argument("account_name")
def _verify_account(account_name):
    """Verifies an account
    Args: account_name (string): name of the account to verify"""

    verify_account(account_name)


def _get_nested_messages(path, obj, message_list):
    """Get nested message list objects from the account"""
    if isinstance(obj, list):
        for index, sub_obj in enumerate(obj):
            _get_nested_messages(path, sub_obj, message_list)
    elif isinstance(obj, dict):
        name = obj.get("name", "")
        if name and isinstance(name, str):
            path = path + ("." if path else "") + name
        for key in obj:
            sub_obj = obj[key]
            if key == "message_list":
                for message in sub_obj:
                    message["path"] = path
                    message_list.append(message)
                continue
            _get_nested_messages(path, sub_obj, message_list)


@create.command("account")
@click.option(
    "--file",
    "-f",
    "account_file",
    type=click.Path(exists=True, file_okay=True, dir_okay=False, readable=True),
    required=True,
    help="Path of Account file to upload",
)
@click.option("--name", "-n", default=None, help="Account name (Optional)")
@click.option(
    "--force",
    "-fc",
    is_flag=True,
    default=False,
    help="Deletes existing account with the same name before create.",
)
@click.option(
    "--auto-verify",
    "-v",
    is_flag=True,
    default=False,
    help="Verifies the account after successfull account creation",
)
def create_account_command(account_file, name, force, auto_verify):
    """
    Creates an account

    Note:

        For ndb/custom_provider account creation the resource type schema variables can be looked by running `calm descrie provider PROVIDER_NAME`
    """

    client = get_api_client()

    if account_file.endswith(".py"):
        res, err = create_account_from_dsl(
            client, account_file, name=name, force_create=force
        )
    else:
        LOG.error("Unknown file format {}".format(account_file))
        return

    if err:
        LOG.error(err["error"])
        return

    account = res.json()

    account_uuid = account["metadata"]["uuid"]
    account_name = account["metadata"]["name"]
    account_status = account.get("status", {})
    account_state = account_status.get("resources", {}).get("state", "DRAFT")
    LOG.debug("Account {} has state: {}".format(account_name, account_state))

    if account_state == "DRAFT":
        msg_list = []
        _get_nested_messages("", account_status, msg_list)

        if not msg_list:
            LOG.error("Account {} created with errors.".format(account_name))
            LOG.debug(json.dumps(account_status))

        msgs = []
        for msg_dict in msg_list:
            msg = ""
            path = msg_dict.get("path", "")
            if path:
                msg = path + ": "
            msgs.append(msg + msg_dict.get("message", ""))

        LOG.error(
            "Account {} created with {} error(s):".format(account_name, len(msg_list))
        )
        click.echo("\n".join(msgs))
        sys.exit(-1)

    LOG.info("Account {} created successfully.".format(account_name))

    context = get_context()
    server_config = context.get_server_config()
    pc_ip = server_config["pc_ip"]
    pc_port = server_config["pc_port"]
    link = "https://{}:{}/dm/self_service/settings/accounts".format(pc_ip, pc_port)
    stdout_dict = {"name": account_name, "link": link, "state": account_state}
    click.echo(json.dumps(stdout_dict, indent=4, separators=(",", ": ")))

    if auto_verify:
        verify_account(account_name)


@compile.command("account")
@click.option(
    "--file",
    "-f",
    "account_file",
    type=click.Path(exists=True, file_okay=True, dir_okay=False, readable=True),
    required=True,
    help="Path of Account file to compile",
)
@click.option(
    "--out",
    "-o",
    "out",
    type=click.Choice(["json", "yaml"]),
    default="json",
    help="output format",
)
def _compile_account_command(account_file, out):
    """Compiles a DSL (Python) acconut into JSON or YAML"""
    compile_account_command(account_file, out)


@update.command("account", feature_min_version="3.0.0")
@click.argument("account_name")
@click.option(
    "--file",
    "-f",
    "account_file",
    type=click.Path(exists=True, file_okay=True, dir_okay=False, readable=True),
    required=True,
    help="Path of Account file to upload",
)
@click.option(
    "--updated-name", "-un", default=None, required=False, help="Updated account name"
)
def _update_account_command(account_file, account_name, updated_name):
    """Updates an account"""

    update_account_command(account_file, account_name, updated_name)
