# Copyright (c) nexB Inc. and others.
# SPDX-License-Identifier: Apache-2.0
#
# Visit https://aboutcode.org and https://github.com/nexB/ for support and download.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from semver import Version

from universal_versions.utils import remove_spaces
from universal_versions.version_range import VersionRange
from universal_versions.versions import parse_version


def find_pessimistic_upper_bound(version_string):
    """
    Helper which returns the version which is pessimistically greater than provided
    'version_string'.

    Example:
    >>find_pessimistic_upper_bound('2.0.8')
    2.1.0
    """
    version_obj = Version.parse(version_string)
    version_tuple = version_obj.to_tuple()
    index_method = {
        0: version_obj.bump_build,
        1: version_obj.bump_minor,
        2: version_obj.bump_patch,
        3: version_obj.bump_prerelease,
    }
    for index, value in enumerate(version_tuple):
        if index > 3:
            raise ValueError(
                f"No pessismistic upper bound exists for the provided version {version_string}"
            )

        if not version_tuple[index + 2]:
            upper_bound_version_object = index_method[index]()
            return upper_bound_version_object.__str__()


def normalized_pessimistic_ranges(pessimistic_version_range_string):
    """
    Helper which returns VersionRange objects from a string which contains ranges which use
    a pessimistic operator. The scheme is 'semver' since only ruby style semver supports
    this operator.

    Example:- '~>2.0.8' will get resolved into VersionRange objects of '>=2.0.8' and '<2.1.0'
    """
    remove_spaces(pessimistic_version_range_string)
    try:
        _, version = pessimistic_version_range_string.split("~>")
    except ValueError:
        raise ValueError(
            f"The version range string {pessimistic_version_range_string} is not valid"
        )

    lower_bound = version
    upper_bound = find_pessimistic_upper_bound(version)

    return VersionRange(f">={lower_bound}", "semver"), VersionRange(f"<{upper_bound}", "semver")


class VersionSpecifier:

    scheme = ""
    ranges = []

    @classmethod
    def from_version_spec_string(cls, version_spec_string):
        """
        Return a VersionSpecifier built from a version spec string, prefixed by
        a scheme such as "semver:1.2.3,>=2.0.0"
        """
        scheme, _, version_range_expressions = version_spec_string.partition(":")
        if not scheme:
            raise ValueError(f"{version_spec_string} is not prefixed by scheme")

        if not version_range_expressions:
            raise ValueError(f"{version_spec_string} contains no version range")

        return cls.from_scheme_version_spec_string(scheme, version_range_expressions)

    @classmethod
    def from_scheme_version_spec_string(cls, scheme, value):
        """
        Return a VersionSpecifier built from a scheme-specific version spec string and a scheme string.
        """

        # TODO: Handle wildcards, carets, tilde here. Convert them into something sane
        value = remove_spaces(value)
        version_ranges = value.split(",")
        ranges = []
        for version_range in version_ranges:
            if scheme == "semver":
                if "~>" in version_range:
                    ranges.extend(normalized_pessimistic_ranges(version_range))
                    continue

            range = VersionRange(version_range, scheme)
            ranges.append(range)

        vs = cls()
        vs.ranges = ranges
        vs.scheme = scheme
        return vs

    def __str__(self):
        """
        Return the canonical representation.
        """
        # TODO: sort to make canonic
        ranges = ",".join(self.ranges)

        return f"{self.scheme}:{ranges}"

    def __contains__(self, version):
        """
        Return True if this VersionSpecifier contains the ``version``
        Version object or scheme-prefixed version string. A version is contained
        in a VersionSpecifier if it satisfies all its Range.
        """
        if isinstance(version, str):
            version = parse_version(version)

        return all([version in version_range for version_range in self.ranges])