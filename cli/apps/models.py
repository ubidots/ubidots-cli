from typing import TypedDict

from cli.apps.enums import MenuAlignmentEnum
from cli.apps.enums import MenuModeEnum


class AppListItem(TypedDict, total=False):
    id: str
    label: str
    name: str
    style: str
    customDomain: str


class MenuResponse(TypedDict):
    menuMode: MenuModeEnum
    menuXml: str
    menuAlignment: MenuAlignmentEnum


class SetMenuPayload(TypedDict):
    menuMode: MenuModeEnum
    menuXml: str
    menuAlignment: MenuAlignmentEnum
