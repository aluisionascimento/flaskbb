# -*- coding: utf-8 -*-
"""
flaskbb.forum.utils
~~~~~~~~~~~~~~~~~~~

Utilities specific to the FlaskBB forums module

:copyright: (c) 2018 the FlaskBB Team
:license: BSD, see LICENSE for more details
"""

from typing import TYPE_CHECKING

from flask import current_app
from flask_login import current_user
from werkzeug.local import LocalProxy

if TYPE_CHECKING:
    from flaskbb.forum.models import Forum
    from flaskbb.user.models import User

from .locals import current_forum


def force_login_if_needed():
    """
    Forces a login if the current user is unauthed and the current forum
    doesn't allow guest users.
    """
    if current_forum and should_force_login(current_user, current_forum):
        return current_app.login_manager.unauthorized()  # pyright: ignore


def should_force_login(
    user: "User | LocalProxy[User | None]", forum: "Forum | LocalProxy[Forum | None]"
):
    """
    Determines if a guest user should be forced to authenticate to access the forum.
    
    This works by checking if the intersection of the forum's allowed groups and 
    the unauthenticated user's groups (which defaults to the Guest group) is empty.
    If they share no groups, the guest cannot access it and must login.
    """
    return not user.is_authenticated and not (
        {g.id for g in forum.groups} & {g.id for g in user.groups}
    )
