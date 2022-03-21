# Copyright 2021 Canonical Ltd.
# See LICENSE file for licensing details.

import shutil

import pytest_asyncio
from helpers import oci_image
from pytest_operator.plugin import OpsTest


@pytest_asyncio.fixture(scope="module", autouse=True)
def copy_loki_library_into_tester_charm(ops_test):
    """Ensure that the tester charm uses the current Loki library."""
    library_path = "lib/charms/loki_k8s/v0/loki_push_api.py"
    install_path = "tests/integration/loki_tester/" + library_path
    shutil.copyfile(library_path, install_path)


@pytest_asyncio.fixture(scope="module")
async def loki_charm(ops_test: OpsTest):
    """Loki charm used for integration testing."""
    charm = await ops_test.build_charm(".")
    return charm


@pytest_asyncio.fixture(scope="module")
async def loki_tester_charm(ops_test):
    """A charm to integration test the Loki charm."""
    charm_path = "tests/integration/loki_tester"
    charm = await ops_test.build_charm(charm_path)
    return charm


@pytest_asyncio.fixture(scope="module")
async def loki_tester_deployment(ops_test, loki_charm, loki_tester_charm):
    """Simple deployment with loki+loki-tester, related."""
    app_names = loki_app_name, loki_tester_app_name = ("loki-k8s", "loki-tester")

    # first deploy loki-k8s, wait for idle, and then
    # deploy the tester. To avoid that if loki-k8s takes long to come up, the
    # tester defers() past his last hook, and we have to wait for update-status
    # to fire.
    await ops_test.model.deploy(
        loki_charm,
        resources={
            "loki-image": oci_image(
                "./metadata.yaml",
                "loki-image",
            )
        },
        application_name=loki_app_name,
    )

    await ops_test.model.wait_for_idle(apps=[loki_app_name], status="active")

    await ops_test.model.deploy(
        loki_tester_charm,
        resources={
            "loki-tester-image": oci_image(
                "./tests/integration/loki_tester/metadata.yaml",
                "loki-tester-image",
            )
        },
        application_name=loki_tester_app_name,
    )

    await ops_test.model.add_relation(
        f"{loki_app_name}:logging", f"{loki_tester_app_name}:log-proxy"
    )

    # before we can expose loki, we need to configure the hostname
    await ops_test.juju("config", loki_app_name, "juju-external-hostname=localhost")

    # todo consider a shorter timeout.
    await ops_test.model.wait_for_idle(apps=app_names, status="active", timeout=60)

    await ops_test.juju("expose", loki_app_name)
    return app_names
