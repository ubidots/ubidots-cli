from typing import Annotated

import typer

from cli.commons.utils import get_instance_key
from cli.commons.utils import simple_lookup_key
from cli.devices import handlers

app = typer.Typer(help="Device management and operations.")


@app.command(short_help="Lists all available devices.")
def list():
    handlers.get_devices()


@app.command(short_help="Retrieves a specific device using its id or label.")
@simple_lookup_key(entity_name="device")
def get(id: str | None = None, label: str | None = None):
    device_key = get_instance_key(id=id, label=label)
    handlers.get_device(device_key=device_key)


@app.command(short_help="Adds a new device.")
def add(
    label: Annotated[str, typer.Argument(help="The label for the device.")],
    name: Annotated[str, typer.Option(help="The name of the device.")] = "",
    description: Annotated[
        str, typer.Option(help="A brief description of the device.")
    ] = "",
    organization: Annotated[
        str, typer.Option(help="The organization associated with the device.")
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
