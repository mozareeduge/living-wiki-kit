#!/usr/bin/env python3
"""Interchange exports for This Wiki — Engine 2.

Deterministic, read-only exports into open standards. Everything emitted is a
DERIVED VIEW: exports never become the system of record (standing reject,
protocol v2 §8), and authority tiers travel intact.

Subcommands:
  prov             JSON-LD (PROV-O 1 + local mw: extensions) knowledge graph:
                   every md record as prov:Entity; source-record -> original
                   chains as prov:hadPrimarySource / prov:wasDerivedFrom from
                   MATERIALS_INDEX; relation participants via mw:hasParticipant
                   (local term - relation_status on disk is free text, so no
                   invented prov:predicate mapping).
  skos             SKOS concept scheme: object folders as collections, records
                   as skos:Concept with prefLabel/altLabel.
  rocrate-check    Validate an existing ro-crate-metadata.json (RO-Crate 1.1+
                   shape used here) if present; otherwise say so plainly.
  tei --source-id  Emit a TEI P5 skeleton (teiHeader/fileDesc/sourceDesc +
                  checksummed witness reference) for one source record.

Outputs land under _exports/interchange/ (git-ignored runtime output).
"""
from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML required", file=sys.stderr)
    raise SystemExit(2)

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "_exports/interchange"
RECORD_DIRS = ["02-sources", "03-objects", "05-claims", "06-relations", "04-notes"]
MANIFEST = ROOT / "00-system/registers/MATERIALS_INDEX.jsonl"

MW = "https://living-wiki-kit.local/ns#"


def parse_fm(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}
    data = yaml.safe_load(text[4:end])
    return data if isinstance(data, dict) else {}


def slug(term: str) -> str:
    text = unicodedata.normalize("NFKD", term)
    return "".join(c for c in text if c.isalnum() or c == "-").lower()


def iter_records():
    for d in RECORD_DIRS:
        base = ROOT / d
        if not base.exists():
            continue
        for p in sorted(base.rglob("*.md")):
            fm = parse_fm(p)
            if fm.get("id"):
                yield p, fm


# ------------------------------------------------------------------ prov

def cmd_prov(_args) -> int:
    entities = []
    index_rows = []
    if MANIFEST.exists():
        for line in MANIFEST.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    index_rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    seen_ids: set[str] = set()
    for p, fm in iter_records():
        rid = str(fm["id"])
        if rid in seen_ids:
            continue
        seen_ids.add(rid)
        ent: dict = {
            "@id": f"mw:{rid}",
            "@type": ["prov:Entity", f"mw:{slug(str(fm.get('type', 'record')))}"],
            "skos:prefLabel": str(fm.get("title", p.stem)),
            "prov:generatedAtTime": str(fm.get("created")) if fm.get("created") else None,
            "mw:authorityTierNote": str(fm.get("current_claim_permission")
                                        or fm.get("validation_status") or ""),
            "visibility": str(fm.get("visibility", "unspecified")),
        }
        rel_status = fm.get("relation_status")
        if rel_status:
            ent["mw:relationStatus"] = str(rel_status)
            # free-text status: deliberately NOT mapped to a prov predicate
        parts = fm.get("participants") or []
        if parts:
            ent["mw:hasParticipant"] = [f"mw:{x}" for x in parts]
        sources = fm.get("supporting_sources") or []
        if sources:
            ent["prov:hadPrimarySource"] = [f"mw:{x}" for x in sources
                                            if isinstance(x, str)]
        entities.append({k: v for k, v in ent.items() if v not in (None, [], "")})

    # extraction chain from the immutable manifest (checksums travel along)
    for row in index_rows:
        orig, rec_id = row.get("original_path"), row.get("id")
        deriv = row.get("extracted_text_path")
        src_rec = row.get("source_record_path")
        if orig and rec_id:
            entities.append({
                "@id": f"file:{orig}",
                "@type": "prov:Entity",
                "skos:prefLabel": f"original: {row.get('filename', orig)}",
                "mw:sha256": row.get("sha256"),
                "mw:preservationStatus": row.get("preservation_status"),
                "_note": "Original artifact; immutable.",
            })
            entities.append({
                "@id": f"mw:{rec_id}",
                "@type": "prov:Entity",
                "prov:hadPrimarySource": {"@id": f"file:{orig}"},
            })
        if deriv and orig:
            entities.append({
                "@id": f"file:{deriv}",
                "@type": "prov:Entity",
                "prov:wasDerivedFrom": {"@id": f"file:{orig}"},
                "mw:extractionQuality": row.get("extraction_quality"),
                "_note": "Derivative remains subordinate (SYSTEM_DESIGN §4.2).",
            })
        if src_rec and orig:
            entities.append({
                "@id": f"file:{src_rec}",
                "@type": "prov:Entity",
                "prov:hadPrimarySource": {"@id": f"file:{orig}"},
            })

    graph = {
        "@context": {
            "prov": "http://www.w3.org/ns/prov#",
            "skos": "http://www.w3.org/2004/02/skos/core#",
            "dcterms": "http://purl.org/dc/terms/",
            "mw": MW,
            "file": "urn:wiki-file:",
        },
        "@graph": sorted(entities, key=lambda e: e["@id"]),
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "prov-graph.jsonld"
    out.write_text(json.dumps(graph, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {out} ({len(graph['@graph'])} nodes)")
    print("scope note: relation_status is free text on disk; participants exported "
          "via local mw:hasParticipant, not fabricated prov:predicate.")
    return 0


# ------------------------------------------------------------------ skos

def cmd_skos(_args) -> int:
    concepts = []
    for p, fm in iter_records():
        rid, t = str(fm["id"]), str(fm.get("title", p.stem))
        concept = {
            "@id": f"mw:{rid}",
            "@type": "skos:Concept",
            "skos:prefLabel": t,
            "skos:notation": rid,
            "mw:recordType": str(fm.get("type", "")),
            "mw:folder": p.parent.relative_to(ROOT).as_posix(),
        }
        aliases = fm.get("alternate_titles") or fm.get("aliases")
        if aliases:
            concept["skos:altLabel"] = [str(a) for a in aliases]
        concepts.append(concept)
    scheme = {
        "@context": {
            "skos": "http://www.w3.org/2004/02/skos/core#",
            "mw": MW,
        },
        "@graph": [{
            "@id": "mw:concept-scheme",
            "@type": "skos:ConceptScheme",
            "dcterms:title": "This Wiki controlled vocabulary (derived view)",
            "skos:hasTopConcept": [],
        }] + concepts,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "skos-concepts.jsonld"
    out.write_text(json.dumps(scheme, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {out} ({len(concepts)} concepts)")
    print("note: semantic relations (broader/narrower) intentionally omitted until "
          "settled hierarchy exists; adding them from candidate material would "
          "violate the fluency rule.")
    return 0


# ------------------------------------------------------------ rocrate

def cmd_rocrate(_args) -> int:
    desc = ROOT / "ro-crate-metadata.json"
    if not desc.exists():
        print("NO DESCRIPTOR: no ro-crate-metadata.json at repo root "
              "(RO-Crate not yet adopted - expected state, not an error).")
        return 0
    crate = ROOT / "ro-crate-metadata.json"
    data = json.loads(crate.read_text(encoding="utf-8"))
    graph = data.get("@graph", [])
    mds = [n for n in graph
           if n.get("@type") in ("MetadataDescriptor", "CreativeWork")
           and str(n.get("about", "")).endswith("./")]
    if not mds:
        print("INVALID: no MetadataDescriptor about ./ in @graph")
        return 1
    problems = []
    for node in graph:
        for part in node.get("hasPart", []) or []:
            pid = part.get("@id") if isinstance(part, dict) else str(part)
            target = ROOT / pid
            if not target.exists():
                problems.append(f"missing hasPart target: {pid}")
    if problems:
        print(f"INVALID: {len(problems)} problem(s)")
        for p in problems[:20]:
            print(f"  - {p}")
        return 1
    print(f"VALID: RO-Crate descriptor ok ({len(graph)} nodes, all hasPart targets exist)")
    return 0


# ------------------------------------------------------------------ tei

TEI_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0" xml:id="{tei_id}">
  <teiHeader>
    <fileDesc>
      <titleStmt><title>{title}</title></titleStmt>
      <publicationStmt><p>This Wiki interchange export; derived view.</p></publicationStmt>
      <sourceDesc>
        <msDesc>
          <msIdentifier>
            <idno type="wiki-id">{mw_id}</idno>
          </msIdentifier>
          <physDesc>
            <objectDesc><p>{format_note}</p></objectDesc>
          </physDesc>
        </msDesc>
      </sourceDesc>
    </fileDesc>
    <encodingDesc>
      <editorialDecl><correction><p>No content correction applied; export only.</p></correction></editorialDecl>
    </encodingDesc>
  </teiHeader>
  <facsimile>
    <!-- surface/zone elements require image manifests; intentionally empty until scans enter intake (T1 backlog item 8 defers IIIF). -->
  </facsimile>
  <body>
    <div type="witness-reference">
      <p>Original artifact: {original}</p>
      <p>SHA-256: {sha256}</p>
      <p>Extraction quality: {quality}. Derivative: {derivative}</p>
    </div>
  </body>
</TEI>
"""


def cmd_tei(args) -> int:
    sid = args.source_id
    rows = []
    if MANIFEST.exists():
        for line in MANIFEST.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                if row.get("id") == sid:
                    rows.append(row)
    if not rows:
        print(f"ERROR: source id not found in MATERIALS_INDEX: {sid}", file=sys.stderr)
        return 1
    row = rows[0]
    xml = TEI_TEMPLATE.format(
        tei_id=sid,
        title=row.get("filename", sid),
        mw_id=sid,
        format_note=f"format={row.get('format')}; pages={row.get('page_count')}; "
                    f"words={row.get('word_count')}",
        original=row.get("original_path", ""),
        sha256=row.get("sha256", ""),
        quality=row.get("extraction_quality", "unknown"),
        derivative=row.get("extracted_text_path", "(none)"),
    )
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"{sid}.tei.xml"
    out.write_text(xml, encoding="utf-8")
    print(f"wrote {out} (P5 skeleton; msDesc fields filled from source record)")
    return 0


# ------------------------------------------------------------------ cli

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("prov").set_defaults(fn=cmd_prov)
    sub.add_parser("skos").set_defaults(fn=cmd_skos)
    sub.add_parser("rocrate-check").set_defaults(fn=cmd_rocrate)
    p = sub.add_parser("tei")
    p.add_argument("--source-id", required=True)
    p.set_defaults(fn=cmd_tei)
    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
