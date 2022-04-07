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
from oci.exceptions import ConfigFileNotFound, InvalidConfig
from oci.exceptions import ServiceError

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
