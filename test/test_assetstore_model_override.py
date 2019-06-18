import pytest
from girder.exceptions import ValidationException
from girder.models.file import File
from girder.models.model_base import Model
from girder.utility import assetstore_utilities
from girder.utility.model_importer import ModelImporter
from girder.utility.abstract_assetstore_adapter import AbstractAssetstoreAdapter


class Fake(Model):
    def initialize(self):
        self.name = 'fake_collection'

    def validate(self, doc):
        return doc


class FakeAdapter(AbstractAssetstoreAdapter):
    def __init__(self, assetstore):
        self.the_assetstore = assetstore


@pytest.fixture
def fakeModel(db):
    ModelImporter.registerModel('fake', Fake, plugin='fake_plugin')

    yield Fake

    ModelImporter.unregisterModel('fake', plugin='fake_plugin')


@pytest.fixture
def fakeAdapter(db):
    assetstore_utilities.setAssetstoreAdapter('fake', FakeAdapter)

    yield

    assetstore_utilities.removeAssetstoreAdapter('fake')


def testAssetstoreModelOverride(fakeModel, fakeAdapter, admin):
    fakeAssetstore = fakeModel().save({
        'foo': 'bar',
        'type': 'fake'
    })
    file = File().createFile(
        creator=admin, item=None, name='a.out', size=0, assetstore=fakeAssetstore,
        assetstoreType=('fake', 'fake_plugin'))

    adapter = File().getAssetstoreAdapter(file)
    assert isinstance(adapter, FakeAdapter)
    assert adapter.the_assetstore == fakeAssetstore


def testAssetstoreModelIsValidated(fakeModel, admin):
    fake = fakeModel().save({})
    with pytest.raises(ValidationException) as exc:
        File().createFile(
            creator=admin, item=None, name='foo', size=0, assetstore=fake, assetstoreType='bad')
    assert str(exc.value) == 'Invalid assetstore type: bad.'
