#!/usr/bin/env python3

from typing import List, Union

from application.DBModels import ServerGroup


def get(group_id: int) -> Union[ServerGroup, None]:
    return ServerGroup.query.get(group_id)