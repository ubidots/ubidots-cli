from typing import Annotated
from typing import no_type_check

import typer

from cli.commons.enums import DefaultInstanceFieldEnum
from cli.commons.utils import get_instance_key
from cli.commons.utils import simple_lookup_key
from cli.devices import handlers

app = typer.Typer(help="Device management and operations.")
DEFAULT_FIELDS = DefaultInstanceFieldEnum.fields()


@app.command(short_help="Retrieves a specific device using its id or label.")
@simple_lookup_key(entity_name="device")
@no_type_check
def get(
    id: str | None = None,
    label: str | None = None,
    fields: Annotated[
        list[str],
        typer.Option(
            help="Comma-separated fields to process. e.g. field1,field2,field3"
        ),
    ] = DEFAULT_FIELDS,
):
    device_key = get_instance_key(id=id, label=label)
    handlers.retrieve_device(device_key=device_key, fields=fields)


@app.command(short_help="Lists all available devices.")
@no_type_check
def list(
    fields: Annotated[
        list[str],
        typer.Option(
            help="Comma-separated fields to process. e.g. field1,field2,field3"
        ),
    ] = DEFAULT_FIELDS,
):
    handlers.list_devices(fields=fields)


@app.command(short_help="Adds a new device.")
def add(
    label: Annotated[str, typer.Argument(help="The label for the device.")],
    name: Annotated[str, typer.Option(help="The name of the device.")] = "",
    description: Annotated[
        str, typer.Option(help="A brief description of the device.")
    ] = "",
    organization: Annotated[
        str,
        typer.Option(
            help="The organization associated with the device. Its id or '['~label'|\\~label]."
        ),
    ] = "",
    tags: Annotated[
        str,
        typer.Option(help="Comma-separated tags for the device. e.g. tag1,tag2,tag3"),
    ] = "",
):
    handlers.add_device(
        label=label,
        name=name,
        description=description,
        organization=organization,
        tags=tags,
    )


@app.command(short_help="Deletes a specific device using its id or label.")
@simple_lookup_key(entity_name="device")
def delete(id: str | None = None, label: str | None = None):
    device_key = get_instance_key(id=id, label=label)
    handlers.delete_device(device_key=device_key)
