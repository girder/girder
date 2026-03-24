import collections

from .bitbucket import Bitbucket
from .box import Box
from .cilogon import CILogon
from .github import GitHub
from .globus import Globus
from .google import Google
from .linkedin import LinkedIn
from .microsoft import Microsoft


def addProvider(provider):
    idMap[provider.getProviderName()] = provider


idMap = collections.OrderedDict()


addProvider(Google)
addProvider(Globus)
addProvider(GitHub)
addProvider(LinkedIn)
addProvider(Bitbucket)
addProvider(Microsoft)
addProvider(Box)
addProvider(CILogon)
