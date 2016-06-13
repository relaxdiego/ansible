from libcloud.common.dimensiondata import API_ENDPOINTS


def get_regions():
    return [region[3:] for region
            in API_ENDPOINTS.keys()
            if region.startswith('dd-')]
