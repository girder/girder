import re
from xml.sax.saxutils import unescape

from girder_worker.docker.io import StreamWriter


class CLIProgressCLIWriter(StreamWriter):
    def __init__(self, job_manager):
        super().__init__()

        self._job_manager = job_manager
        self._buf = b''
        self._state = None
        re_start = re.compile('<filter-start>.*</filter-start>[\\s]*', re.MULTILINE | re.DOTALL)
        re_end = re.compile('<filter-end>.*</filter-end>[\\s]*', re.MULTILINE | re.DOTALL)
        re_time = re.compile('<filter-time>[^<]*</filter-time>[\\s]*', re.MULTILINE)
        re_stage_progress = re.compile(
            '<filter-stage-progress>[^<]*</filter-stage-progress>[\\s]*', re.MULTILINE)

        self._re_progress = re.compile('<filter-progress>([^<]*)</filter-progress>[\\s]*',
                                       re.MULTILINE)
        self._re_name = re.compile('<filter-name>([^<]*)</filter-name>[\\s]*', re.MULTILINE)
        self._re_comment = re.compile('<filter-comment>([^<]*)</filter-comment>[\\s]*',
                                      re.MULTILINE)

        self._re_clean = [re_start, re_end, re_time, re_stage_progress, self._re_progress,
                          self._re_name, self._re_comment]

        self._last_name = 'Unknown'
        self._last_comment = ''

    def forward(self, buf):
        self._job_manager.write(buf)

    def write(self, buf):
        act = self._buf + buf
        self._buf = b''

        if b'</filter-' not in act:
            if b'<filter-' in act:
                # cache for next time
                self._buf = act
                return
            return self.forward(act)

        t = act.decode('utf-8')

        self._update(t)

        for clean in self._re_clean:
            if not t:
                break
            t = clean.sub('', t)
        if t:
            self.forward(t.encode('utf-8'))

    def _update(self, text):
        name = self._re_name.findall(text)
        comment = self._re_comment.findall(text)
        progress = self._re_progress.findall(text)

        if name:
            self._last_name = unescape(name[-1]).strip()
        if comment:
            self._last_comment = unescape(comment[-1]).strip()

        msg = self._last_comment if self._last_comment else self._last_name

        if progress:
            val = float(progress[-1])
            self._job_manager.updateProgress(total=1, current=val, message=msg)

    def close(self):
        # flush rest
        if self._buf:
            self.forward(self._buf)
            self._buf = ''
