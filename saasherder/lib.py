#!/usr/bin/env python
"""
Common utilities to be used by other modules
"""


def split_repo_name(repo_name):
    """
    Splits a container repository into its parts viz
    [registry, namespace, image, tag]
    Given a correct repo_name, returns

    split_repo_name("r.c.o/prod/foo/bar:tag1")
    {'image': 'prod/foo/bar:tag1',
     'image_name': 'prod/foo/bar',
     'registry': 'r.c.o',
     'tag': 'tag1'
    }
    """

    if not repo_name:
        return {}

    parts = repo_name.strip().split("/")

    if len(parts) == 1:
        # case for foo:latest
        registry = None
        image = repo_name

    elif len(parts) == 2:
        # check if part[0] is a registry
        # colon check for host:port
        if "." in parts[0] or ":" in parts[0]:
            # case for r.c.o/foo:latest
            registry = parts[0]
            image = parts[1]
        else:
            # case for foo/bar:latest
            registry = None
            image = repo_name

    # for cases where len(parts) > 2
    else:
        # check if part[0] is a registry
        if "." in parts[0] or ":" in parts[0]:
            # case for r.c.o/foo/bar:latest
            registry = parts[0]
            image = "/".join(parts[1:])
        else:
            # case for prod/foo/bar:latest
            registry = None
            image = repo_name

    # now process tags
    image_parts = image.split(":")
    if len(image_parts) == 2:
        # case for foo:tag1, foo/bar:tag1, prod/foo/bar:latest
        image_name = image_parts[0]
        tag = image_parts[1]
    else:
        # cases for foo , foo/bar, prod/foo/bar
        image_name = image
        # use default tag
        tag = "latest"

    return {"registry": registry,
            "image": image,
            "image_name": image_name,
            "tag": tag}
