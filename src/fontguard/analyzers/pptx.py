from fontguard.analyzers.office import OfficeAnalyzer


class PPTXAnalyzer(OfficeAnalyzer):
    extensions = frozenset({".pptx"})
    prefix = "ppt/"
