# -*- coding: utf-8 -*-
import collections

from .google import Google
from .globus import Globus
from .github import GitHub
from .linkedin import LinkedIn
from .bitbucket import Bitbucket
from .box import Box
from .synapse import Synapse


def addProvider(provider):
    idMap[provider.getProviderName()] = provider


idMap = collections.OrderedDict()


addProvider(Google)
addProvider(Globus)
addProvider(GitHub)
addProvider(LinkedIn)
addProvider(Bitbucket)
addProvider(Box)
addProvider(Synapse)
