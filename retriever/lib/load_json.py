from __future__ import division
from __future__ import print_function

from future import standard_library

standard_library.install_aliases()
from builtins import zip
from builtins import str
import json
import sys
import pprint
from collections import OrderedDict
from retriever.lib.templates import TEMPLATES
from retriever.lib.models import myTables
from retriever.lib.tools import open_fr

if sys.version_info[0] < 3:
    from codecs import open


def read_json(json_file, debug=False):
    """Read Json dataset package files"""
    json_object = OrderedDict()
    json_file = str(json_file) + ".json"

    try:
        json_object = json.load(open_fr(json_file))
    except ValueError:
        pass
    if type(json_object) is dict and "resources" in json_object.keys():

        # Note::formats described by frictionlessdata data may need to change
        tabular_formats = ["csv", "tab"]
        vector_formats = ["shp", "kmz"]
        raster_formats = ["tif","tiff" "bil", ".hdr", "h5","hdf5", "hr", "image"]

        for resource_item in json_object["resources"]:
            if "format" in resource_item:
                if resource_item["format"] in tabular_formats:
                    resource_item["format"] = "tabular"
                elif resource_item["format"] in vector_formats:
                    resource_item["format"] = "vector"
                elif resource_item["format"] in raster_formats:
                    resource_item["format"] = "raster"
            else:
                resource_item["format"] = "tabular"

            # Check for required resource fields
            spec_list = ["name", "url"]

            rspec = set(spec_list)
            if not rspec.issubset(resource_item.keys()):
                raise ValueError("One of the required attributes is missing from the {} dataset script.\
                    Make sure it has all of the following attributes: {}".format(json_file, rspec))

            for spec in spec_list:
                if not resource_item[spec]:
                    raise ValueError("Check either {} for missing values.\n Package {}".format(rspec, json_file))

        json_object["tables"] = {}
        temp_tables = {}
        table_names = [item["name"] for item in json_object["resources"]]
        temp_tables["tables"] = dict(zip(table_names, json_object["resources"]))

        for table_name, table_spec in temp_tables["tables"].items():
            json_object["tables"][table_name] = myTables[temp_tables["tables"][table_name]["format"]](**table_spec)
        json_object.pop("resources", None)

        return TEMPLATES["default"](**json_object)
    return None
