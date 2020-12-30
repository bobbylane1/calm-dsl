import sys

from .entity import EntityType
from calm.dsl.log import get_logging_handle

LOG = get_logging_handle(__name__)


# Project


class ProjectType(EntityType):
    __schema_name__ = "Project"
    __openapi_type__ = "project"

    def compile(cls):
        cdict = super().compile()

        cdict["account_reference_list"] = []

        # Populate accounts
        provider_list = cdict.pop("provider_list", [])
        for provider_obj in provider_list:
            provider_type = provider_obj["provider_type"]
            if provider_type == "nutanix_pc":
                if "subnet_reference_list" in provider_obj:
                    if cdict.get("subnet_reference_list") is None:
                        cdict["subnet_reference_list"] = []
                    cdict["subnet_reference_list"].extend(provider_obj["subnet_reference_list"])

                elif "external_network_list" in provider_obj:
                    if cdict.get("external_network_list") is None:
                        cdict["external_network_list"] = []
                    cdict["external_network_list"].extend(provider_obj["external_network_list"])

                if "default_subnet_reference" in provider_obj:
                    cdict["default_subnet_reference"] = provider_obj[
                        "default_subnet_reference"
                    ]

            cdict["account_reference_list"].append(provider_obj["account_reference"])

        quotas = cdict.pop("quotas", None)
        if quotas:
            project_resources = []
            for qk, qv in quotas.items():
                if qk != "VCPUS":
                    qv *= 1073741824

                project_resources.append({"limit": qv, "resource_type": qk})

            cdict["resource_domain"] = {"resources": project_resources}

        # pop out unnecessary attibutes
        cdict.pop("environment_definition_list", None)

        return cdict


def project(**kwargs):
    name = kwargs.get("name", None)
    bases = ()
    return ProjectType(name, bases, kwargs)


Project = project()
