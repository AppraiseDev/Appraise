#!/usr/bin/env python3
import argparse
import copy
import sys

import lxml.etree as ET


def main():
    tree = ET.parse(sys.stdin)

    KEEP_SYSTEMS = "Online-A Online-B Online-W Online-Y".split()
    KEEP_DOCS = (
        "abendzeitung-muenchen.de.275234 bild.254846 epochtimes.de.56046 faz.79571 "
        "handelsblatt.com.292800 haz.de.150673 kurier.at.204564 ln-online.de.149803 "
        "mittelbayerische.de.307175 mt-online.de.23946 nzz.ch.79514 "
        "oberpfalznetz.de.99395 pnp.de.390035 rt-german.14747 salzburg.com.306596"
    ).split()

    for doc in tree.getroot().findall(".//doc"):
        doc_id = doc.attrib["id"]
        if doc_id not in KEEP_DOCS:
            doc.getparent().remove(doc)

    for hyp in tree.getroot().findall(".//hyp"):
        hyp_id = hyp.attrib["system"]
        if hyp_id not in KEEP_SYSTEMS:
            hyp.getparent().remove(hyp)

    output = ET.tostring(
        tree, pretty_print=True, xml_declaration=True, encoding='utf-8'
    ).decode()
    sys.stdout.write(output)


if __name__ == "__main__":
    main()
