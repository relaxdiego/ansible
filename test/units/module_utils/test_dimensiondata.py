from mock import patch

from ansible.module_utils import dimensiondata as subject


class TestGetRegion:

    @patch('ansible.module_utils.dimensiondata.API_ENDPOINTS', autospec=True)
    def test__return_keys_without_prefix(self, api_endpoints):
        # Mock
        dd_regions = ['dd-ep1', 'dd-ep2', 'dd-ep3']
        other_regions = ['ec2-ep1', 'ose-ep2', 'xx-epdd']
        api_endpoints.keys.return_value = dd_regions + other_regions

        # Exercise
        returned = subject.get_regions()

        # Validate
        assert(1 == api_endpoints.keys.call_count)

        expected = [region[3:] for region in dd_regions]
        assert(expected == returned)
