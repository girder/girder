from unittest import mock

import pytest

from slicer_cli_web.girder_worker_plugin.cli_progress import CLIProgressCLIWriter


@pytest.mark.plugin('slicer_cli_web')
class Test:
    def setup_method(self):
        job_manager = mock.Mock()
        self.write = job_manager.write = mock.MagicMock()
        self.updateProgress = job_manager.updateProgress = mock.MagicMock()
        self.w = CLIProgressCLIWriter(job_manager)

    def test_simple(self):
        self.w.write(b'Test')
        self.write.assert_called_once_with(b'Test')
        self.updateProgress.assert_not_called()

    @pytest.mark.parametrize('tag', [
        b'<filter-start>Dummy</filter-start>',
        b'<filter-end>Dummy</filter-end>',
        b'<filter-time>0.2</filter-time>',
        b'<filter-stage-progress>0.2</filter-stage-progress>',
        b'<filter-name>Dummy</filter-name>',
        b'<filter-comment>Dummy</filter-comment>',
        b"""<filter-start>
            <filter-name>Dummy</filter-name>
            <filter-comment>Dummy</filter-comment>
            </filter-start>""",
        b"""<filter-end>
            <filter-name>Dummy</filter-name>
            <filter-time>0.2</filter-time>
            </filter-end>""",
    ])
    def test_filter(self, tag):
        self.w.write(b'%sTest' % tag)
        self.write.assert_called_once_with(b'Test')
        self.updateProgress.assert_not_called()

    def test_progress(self):
        self.w.write(b"""<filter-start>
        <filter-name>Dummy</filter-name>
        <filter-comment>Comment</filter-comment>
        </filter-start>Test""")
        self.write.assert_called_once_with(b'Test')
        self.updateProgress.assert_not_called()

        self.write.reset_mock()
        self.w.write(b"""<filter-progress>0.1</filter-progress>Test""")
        self.write.assert_called_once_with(b'Test')
        self.updateProgress.assert_called_once_with(total=1, current=0.1, message='Comment')

    def test_progress_only(self):
        self.w.write(b"""<filter-progress>0.1</filter-progress>Test""")
        self.write.assert_called_once_with(b'Test')
        self.updateProgress.assert_called_once_with(total=1, current=0.1, message='Unknown')

    def test_multi_stage(self):
        self.w.write(b"""<filter-progress>0.1""")
        self.write.assert_not_called()
        self.w.write(b"""</filter-progress>Test""")
        self.write.assert_called_once_with(b'Test')
        self.updateProgress.assert_called_once_with(total=1, current=0.1, message='Unknown')

    def test_multi_stage_invalid(self):
        self.w.write(b"""<filter-progress>0.1""")
        self.write.assert_not_called()
        self.w.close()
        self.write.assert_called_once_with(b'<filter-progress>0.1')
        self.updateProgress.assert_not_called()
