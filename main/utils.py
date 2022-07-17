
import inspect
import os
import re
import importlib
import sys

import main.plugins


def get_resources(loc, qs=None, acc=None):
    if acc is None:
        acc = []
    acc += list(getattr(loc, qs).all())
    if hasattr(loc, 'nested') and loc.nested:
        for l in loc.nested.all():
            get_resources(l, qs, acc)
    return acc


def get_classes(module) -> list:
    classes = []

    if module:

        classes += inspect.getmembers(
                module,
                lambda member: inspect.isclass(member) and member.__module__ == module.__name__
        )

    return [(x[0], x[0]) for x in classes]


def instance_klass(module, klass, **kwargs):
    return getattr(module, klass)(**kwargs)