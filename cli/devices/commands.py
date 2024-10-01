from typing import Annotated
from typing import no_type_check

import typer

from cli.commons.decorators import add_fields_option
from cli.commons.decorators import add_filter_option
from cli.commons.decorators import add_pagination_options
from cli.commons.decorators import add_sort_by_option
from cli.commons.decorators import simple_lookup_key
from cli.commons.enums import DefaultInstanceFieldEnum
from cli.commons.enums import EntityNameEnum
from cli.commons.utils import get_instance_key
from cli.commons.validators import is_valid_json_string
from cli.devices import handlers

app = typer.Typer(help="Device management and operations.")


@app.command(short_help="Deletes a specific device using its id or label.")
@simple_lookup_key(entity_name=EntityNameEnum.DEVICE)
def delete(id: str | None = None, label: str | None = None):
    device_key = get_instance_key(id=id, label=label)
    handlers.delete_device(device_key=device_key)


@app.command(short_help="Retrieves a specific device using its id or label.")
@simple_lookup_key(entity_name=EntityNameEnum.DEVICE)
@add_fields_option()
@no_type_check
def get(
    id: str | None = None,
    label: str | None = None,
    fields: str = DefaultInstanceFieldEnum.get_default_fields(),
):
    device_key = get_instance_key(id=id, label=label)
    handlers.retrieve_device(device_key=device_key, fields=fields)


@app.command(short_help="Lists all available devices.")
@add_fields_option()
@add_pagination_options()
@add_sort_by_option()
@add_filter_option()
@no_type_check
def list(
    fields: str = DefaultInstanceFieldEnum.get_default_fields(),
    filter: str | None = None,
    sort_by: str | None = None,
    page_size: int | None = None,
    page: int | None = None,
):
    handlers.list_devices(
        fields=fields,
        filter=filter,
        sort_by=sort_by,
        page_size=page_size,
        page=page,
    )


@app.command(short_help="Adds a new device.")
def add(
    label: Annotated[
        str, typer.Argument(help="The label for the device.", show_default=False)
    ],
    name: Annotated[str, typer.Option(help="The name of the device.")] = "",
    description: Annotated[
        str, typer.Option(help="A brief description of the device.")
    ] = "",
    organization: Annotated[
        str,
        typer.Option(
            help="The organization associated with the device. Its id or ['~label' | \\~label]."
        ),
    ] = "",
    tags: Annotated[
        str,
        typer.Option(help="Comma-separated tags for the device. e.g. tag1,tag2,tag3"),
    ] = "",
    properties: Annotated[
        str,
        typer.Option(
            help="Device properties in JSON format.", callback=is_valid_json_string
        ),
    ] = "{}",
):
    handlers.add_device(
        label=label,
        name=name,
        description=description,
        organization=organization,
        tags=tags,
        properties=properties,
    )


@app.command(short_help="Update a device.")
@simple_lookup_key(entity_name=EntityNameEnum.DEVICE)
def update(
    id: str | None = None,
    label: str | None = None,
    new_label: Annotated[str, typer.Option(help="The label for the device.")] = "",
    new_name: Annotated[str, typer.Option(help="The name of the device.")] = "",
    description: Annotated[
        str, typer.Option(help="A brief description of the device.")
    ] = "",
    organization: Annotated[
        str,
        typer.Option(
            help="The organization associated with the device. Its id or ['~label' | \\~label]."
        ),
    ] = "",
    tags: Annotated[
        str,
        typer.Option(help="Comma-separated tags for the device. e.g. tag1,tag2,tag3"),
    ] = "",
    properties: Annotated[
        str,
        typer.Option(
            help="Device properties in JSON format.", callback=is_valid_json_string
        ),
    ] = "{}",
):
    device_key = get_instance_key(id=id, label=label)
    handlers.update_device(
        device_key=device_key,
        label=new_label,
        name=new_name,
        description=description,
        organization=organization,
        tags=tags,
        properties=properties,
    )
