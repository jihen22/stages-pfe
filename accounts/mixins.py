"""Reusable access-control helpers: login required + role required."""

from functools import wraps

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied


class RoleRequiredMixin(LoginRequiredMixin):
    """Class-based-view mixin restricting access to a set of roles.

    Always enforces (1) the user is authenticated and (2) the user's role is
    part of ``allowed_roles``. On mismatch Django raises ``PermissionDenied``
    which renders the project ``403.html`` page.
    """

    allowed_roles = ()

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if self.allowed_roles and request.user.role not in self.allowed_roles:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


def role_required(*roles):
    """Function-based-view decorator equivalent of :class:`RoleRequiredMixin`."""

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if request.user.role not in roles:
                raise PermissionDenied
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator
