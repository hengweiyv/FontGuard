from fontguard.analyzers.office import OfficeAnalyzer


class DOCXAnalyzer(OfficeAnalyzer):
    extensions = frozenset({".docx"})
    prefix = "word/"
