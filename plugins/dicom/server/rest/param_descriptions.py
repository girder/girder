#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright Kitware Inc.
#
#  Licensed under the Apache License, Version 2.0 ( the "License" );
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
###############################################################################

# QIDO-RS
SearchForDescription = "Searches for DICOM %s that match specified search parameters and returns a" \
                       "list of matching %s and the requested attributes for each %s."

QueryParamDescription = "{attributeID}={value}"
FuzzyMatchingParamDescription = "Set to 'true' to perform additional fuzzy semantic matching of person names."
LimitParamDescription = "If the limit query key is not specified or its value exceeds the total number" \
                        " of matching results then {maximumResults} is the lesser of the number of matching" \
                        "results and the maximum number of results supported by the Server."
OffsetParamDescription = "If the offset query key is not specified or its value is less than zero then it defaults to zero."
