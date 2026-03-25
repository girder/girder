from girder.utility.webroot import WebrootBase


def testEscapeJavascript():
    # Don't escape alphanumeric characters
    alphaNumString = 'abcxyz0189ABCXYZ'
    assert WebrootBase._escapeJavascript(alphaNumString) == alphaNumString

    # Do escape everything else
    dangerString = 'ab\'"<;>\\YZ'
    assert WebrootBase._escapeJavascript(dangerString) == \
        'ab\\u0027\\u0022\\u003C\\u003B\\u003E\\u005CYZ'


def testWebRootTemplateFilename():
    """
    Test WebrootBase.templateFilename attribute after initialization
    and after setting a custom template path.
    """
    webroot = WebrootBase(templatePath='/girder/base_template.mako')
    assert webroot.templateFilename == 'base_template.mako'

    webroot.setTemplatePath('/plugin/custom_template.mako')
    assert webroot.templateFilename == 'custom_template.mako'
