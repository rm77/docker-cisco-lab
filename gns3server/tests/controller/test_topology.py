#!/usr/bin/env python
#
# Copyright (C) 2016 GNS3 Technologies Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import json
import uuid
import pytest
import aiohttp
from unittest.mock import MagicMock
from tests.utils import asyncio_patch

from gns3server.controller.project import Project
from gns3server.controller.compute import Compute
from gns3server.controller.topology import project_to_topology, load_topology, GNS3_FILE_FORMAT_REVISION
from gns3server.version import __version__


def test_project_to_topology_empty(tmpdir):
    project = Project(name="Test")
    topo = project_to_topology(project)
    assert topo == {
        "project_id": project.id,
        "name": "Test",
        "auto_start": False,
        "auto_close": True,
        "auto_open": False,
        "scene_width": 2000,
        "scene_height": 1000,
        "revision": GNS3_FILE_FORMAT_REVISION,
        "zoom": 100,
        "show_grid": False,
        "show_interface_labels": False,
        "show_layers": False,
        "snap_to_grid": False,
        "topology": {
            "nodes": [],
            "links": [],
            "computes": [],
            "drawings": []
        },
        "type": "topology",
        "version": __version__
    }


def test_basic_topology(tmpdir, async_run, controller):
    project = Project(name="Test", controller=controller)
    compute = Compute("my_compute", controller)
    compute.http_query = MagicMock()

    with asyncio_patch("gns3server.controller.node.Node.create"):
        node1 = async_run(project.add_node(compute, "Node 1", str(uuid.uuid4()), node_type="qemu"))
        node2 = async_run(project.add_node(compute, "Node 2", str(uuid.uuid4()), node_type="qemu"))

    link = async_run(project.add_link())
    async_run(link.add_node(node1, 0, 0))
    with asyncio_patch("gns3server.controller.udp_link.UDPLink.create") as mock_udp_create:
        async_run(link.add_node(node2, 0, 0))

    drawing = async_run(project.add_drawing(svg="<svg></svg>"))

    topo = project_to_topology(project)
    assert len(topo["topology"]["nodes"]) == 2
    assert node1.__json__(topology_dump=True) in topo["topology"]["nodes"]
    assert topo["topology"]["links"][0] == link.__json__(topology_dump=True)
    assert topo["topology"]["computes"][0] == compute.__json__(topology_dump=True)
    assert topo["topology"]["drawings"][0] == drawing.__json__(topology_dump=True)


def test_load_topology(tmpdir):
    data = {
        "project_id": "69f26504-7aa3-48aa-9f29-798d44841211",
        "name": "Test",
        "revision": GNS3_FILE_FORMAT_REVISION,
        "topology": {
            "nodes": [],
            "links": [],
            "computes": [],
            "drawings": []
        },
        "type": "topology",
        "version": __version__}

    path = str(tmpdir / "test.gns3")
    with open(path, "w+") as f:
        json.dump(data, f)
    topo = load_topology(path)
    assert topo == data


def test_load_topology_file_error(tmpdir):
    path = str(tmpdir / "test.gns3")
    with pytest.raises(aiohttp.web.HTTPConflict):
        topo = load_topology(path)


def test_load_topology_file_error_schema_error(tmpdir):
    path = str(tmpdir / "test.gns3")
    with open(path, "w+") as f:
        json.dump({
            "revision": GNS3_FILE_FORMAT_REVISION
        }, f)
    with pytest.raises(aiohttp.web.HTTPConflict):
        topo = load_topology(path)


def test_load_newer_topology(tmpdir):
    """
    If a topology is design for a more recent GNS3 version
    we disallow the loading.
    """
    data = {
        "project_id": "69f26504-7aa3-48aa-9f29-798d44841211",
        "name": "Test",
        "revision": 42,
        "topology": {
        },
        "type": "topology",
        "version": __version__}

    path = str(tmpdir / "test.gns3")
    with open(path, "w+") as f:
        json.dump(data, f)
    with pytest.raises(aiohttp.web.HTTPConflict):
        topo = load_topology(path)
