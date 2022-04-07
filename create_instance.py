#!/usr/bin/env python3
"""
Create Oracle Cloud Compute Instance
"""


import sys
import logging
from os import getenv

from oci.config import validate_config
from oci.config import from_file
from oci.identity import IdentityClient
from oci.response import Response
from oci.core import ComputeClient
from oci.core import VirtualNetworkClient
from oci.exceptions import ConfigFileNotFound, InvalidConfig
from oci.exceptions import ServiceError
from oci.core.models import InstanceConfigurationLaunchInstanceDetails
from oci.core.models import InstanceConfigurationInstanceSourceViaImageDetails
from oci.core.models import InstanceConfigurationCreateVnicDetails
from oci.core.models import InstanceConfigurationAvailabilityConfig
from oci.core.models import InstanceConfigurationLaunchInstanceShapeConfigDetails
from oci.core.models import InstanceConfigurationInstanceOptions

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(name)s %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


try:
    config = from_file()
    validate_config(config)
except (ConfigFileNotFound, InvalidConfig) as e:
    logger.error("config file error: %s", e)
    sys.exit(1)

compartment_id = config["tenancy"]


def get_res_value(res: Response, attr):
    """
    Get attribute value from oci.response.Response object
    """
    try:
        if isinstance(res.data, list):
            return res.data[0].__getattribute__(attr)
        return res.data.__getattribute__(attr)
    except (AttributeError, IndexError) as err:
        logger.error("couldn't get response %s value: %s",
                     res.request.response_type, err)
        sys.exit(1)


shape = getenv("SHAPE")
if shape is None:
    logger.error("shape is not set")
    sys.exit(1)
logger.info("shape: %s", shape)

operating_system = getenv("OPERATING_SYSTEM")
operating_system_version = getenv("OPERATING_SYSTEM_VERSION")
image_name = None
if operating_system is None or operating_system_version is None:
    logger.warning("OPERATING_SYSTEM and OPERATING_SYSTEM_VERSION is not set")
    cnt = 0
    while image_name is None:
        cnt += 1
        if cnt > 3:
            logger.error("couldn't get image name")
            sys.exit(1)
        image_name = input("Enter image name: ") or None


id_client = IdentityClient(config)

domain_name = getenv("DOMAIN_NAME")
if domain_name is None:
    try:
        domain_name = get_res_value(
            id_client.list_availability_domains(compartment_id), "name")
    except ServiceError as e:
        logger.error("couldn't get domain name: %s", e)
        sys.exit(1)
logger.info("domain name: %s", domain_name)

compute_client = ComputeClient(config)

try:
    image_id = get_res_value(compute_client.list_images(compartment_id,
                                                        operating_system=operating_system,
                                                        operating_system_version=operating_system_version,
                                                        display_name=image_name,
                                                        sort_by="TIMECREATED"), "id")
except ServiceError as e:
    logger.error("couldn't get image id: %s", e)
    sys.exit(1)
else:
    logger.info("image id: %s", image_id)

vn_client = VirtualNetworkClient(config)
subnet_name = getenv("SUBNET_NAME")
# Get subnet id by subnet name, if subnet name is not set, get latest subnet's id
try:
    subnet_id = get_res_value(vn_client.list_subnets(
        compartment_id, display_name=subnet_name, sort_by='TIMECREATED'), 'id')
except ServiceError as e:
    logger.error("couldn't get subnet id: %s", e)
    sys.exit(1)


# Construct oci.core.models.InstanceConfigurationInstanceOptions object,
# which is used to create oci.core.models.InstanceConfigurationLaunchInstanceDetails.
instance_options = InstanceConfigurationInstanceOptions(
    are_legacy_imds_endpoints_disabled=False)

# Construct oci.core.models.InstanceConfigurationLaunchInstanceShapeConfigDetails,
# which is used to create oci.core.models.InstanceConfigurationLaunchInstanceDetails.
ocpus = getenv("OCPU")
memory_in_gbs = getenv("MEMORY_IN_GB")
shape_config = InstanceConfigurationLaunchInstanceShapeConfigDetails(
    ocpus=ocpus, memory_in_gbs=memory_in_gbs)

# Construct oci.core.models.InstanceConfigurationAvailabilityConfig object,
# which is used to create oci.core.models.InstanceConfigurationLaunchInstanceDetails.
#  Allowed values for this property are: "RESTORE_INSTANCE", "STOP_INSTANCE"
recovery_action = getenv("RECOVERY_ACTION", "RESTORE_INSTANCE")
availability_config = InstanceConfigurationAvailabilityConfig(
    recovery_action=recovery_action)

# Construct oci.core.models.InstanceConfigurationCreateVnicDetails object,
# which is used to create oci.core.models.InstanceConfigurationLaunchInstanceDetails.
assign_public_ip = bool(getenv("ASSIGN_PUBLIC_IP"))
create_vnic_details = InstanceConfigurationCreateVnicDetails(
    assign_public_ip=assign_public_ip, assign_private_dns_record=True, subnet_id=subnet_id)

# Construct oci.core.models.InstanceConfigurationInstanceSourceViaImageDetails object,
# it's a subclass of InstanceConfigurationInstanceSourceDetails,
# which is used to create oci.core.models.InstanceConfigurationLaunchInstanceDetails.
source_details = InstanceConfigurationInstanceSourceViaImageDetails(
    source_type="image", image_id=image_id)

# Construct oci.core.models.InstanceConfigurationLaunchInstanceDetails object,
# which is used to create oci.core.models.InstanceConfigurationInstanceDetails.
launch_details = InstanceConfigurationLaunchInstanceDetails(compartment_id=compartment_id,
                                                            availability_domain=domain_name,
                                                            shape=shape,
                                                            shape_config=shape_config,
                                                            availability_config=availability_config,
                                                            instance_options=instance_options,
                                                            source_details=source_details,
                                                            create_vnic_details=create_vnic_details)
