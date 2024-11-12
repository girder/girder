import sys
import time
from xml.sax.saxutils import escape


class ProgressHelper:
    def __init__(self, name, comment=''):
        self.name = name
        self.comment = comment
        self.start = time.time()

    def __enter__(self):
        print("""<filter-start>
<filter-name>%s</filter-name>
<filter-comment>%s</filter-comment>
</filter-start>""" % (escape(str(self.name)), escape(str(self.comment))))
        sys.stdout.flush()
        self.start = time.time()
        return self

    def progress(self, val):
        print("""<filter-progress>%s</filter-progress>""" % val)
        sys.stdout.flush()

    def message(self, comment):
        self.comment = comment
        print("""<filter-comment>%s</filter-comment>""" % escape(str(comment)))
        sys.stdout.flush()

    def name(self, name):
        # Leave the original name alone
        print("""<filter-name>%s</filter-name>""" % escape(str(name)))
        sys.stdout.flush()

    def __exit__(self, exc_type, exc_val, exc_tb):
        end = time.time()
        duration = end - self.start
        print("""<filter-end>
 <filter-name>%s</filter-name>
 <filter-time>%s</filter-time>
</filter-end>""" % (escape(str(self.name)), duration))
        sys.stdout.flush()


__all__ = ['ProgressHelper']
