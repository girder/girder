

from . dicomrs import (dicomStudies, dicomSeries, dicomInstances)


def load(info):
    info['apiRoot'].studies = dicomStudies()
    info['apiRoot'].series = dicomSeries()
    info['apiRoot'].instances = dicomInstances()

