from pathlib import Path
from zipfile import ZipFile

from defusedxml import ElementTree

from fontguard.analyzers.base import Analyzer
from fontguard.core.models import AnalysisResult, DetectedFont, Evidence

MAX_MEMBER = 16 * 1024 * 1024
MAX_ARCHIVE = 128 * 1024 * 1024


class OfficeAnalyzer(Analyzer):
    prefix = ""

    def analyze(self, path: Path) -> AnalysisResult:
        result = AnalysisResult()
        names: dict[str, DetectedFont] = {}
        with ZipFile(path) as archive:
            members = [
                i
                for i in archive.infolist()
                if i.filename.startswith(self.prefix) and i.filename.endswith(".xml")
            ]
            if len(members) > 10000 or sum(i.file_size for i in members) > MAX_ARCHIVE:
                raise ValueError("Office XML exceeds archive resource limits.")
            for member in members:
                if member.file_size > MAX_MEMBER:
                    raise ValueError(f"Office XML member exceeds size limit: {member.filename}")
                root = ElementTree.fromstring(archive.read(member))
                for element in root.iter():
                    tag = element.tag.rsplit("}", 1)[-1]
                    for attr, value in element.attrib.items():
                        attr = attr.rsplit("}", 1)[-1]
                        if (
                            attr != "typeface"
                            and not (
                                tag == "rFonts" and attr in {"ascii", "hAnsi", "eastAsia", "cs"}
                            )
                            and not (tag == "font" and attr == "name")
                        ):
                            continue
                        if not value or value.startswith("+"):
                            continue
                        evidence = Evidence(
                            type="office_xml",
                            file=str(path),
                            member=member.filename,
                            raw_font_name=value,
                            details={"tag": tag, "attribute": attr, "declaration_only": True},
                        )
                        if value in names:
                            names[value].evidence.append(evidence)
                        else:
                            detected = DetectedFont(
                                source_file=str(path),
                                font_family=value,
                                detection_method="office_xml",
                                evidence=[evidence],
                            )
                            names[value] = detected
                            result.fonts.append(detected)
            # Never assert embedding from a font table declaration alone.
            embedded = [
                i.filename
                for i in archive.infolist()
                if i.filename.startswith(self.prefix + "fonts/")
            ]
            if embedded:
                for detected in result.fonts:
                    detected.evidence.append(
                        Evidence(
                            type="office_embedded_inventory",
                            file=str(path),
                            details={"members": embedded, "mapping_verified": False},
                        )
                    )
        return result
