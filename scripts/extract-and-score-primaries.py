#!/usr/bin/env python3

# 
# Read the primaries from the ocelot dump, create the xml and txt versions for release, and score them
#


import argparse
import copy
import csv
import glob
import io
import logging
import os
import sacrebleu
import sys

import lxml.etree as ET

from pathlib import Path
import wmtformat


LOG = logging.getLogger(__name__)

def map_name(name):
  """Apply any conversions to names"""
  if name == "Nemo":
    name = "NVIDIA-NeMo"
  return name

def extract_text(xml_file, out_dir, prefix, pair, testsuites):
  src_lang, src, ref_lang, ref, hyp_lang, hyp = wmtformat.unwrap(xml_file.as_posix(), no_testsuites = not testsuites)
  # sources
  src_dir = out_dir / "sources"
  src_dir.mkdir(exist_ok=True)
  src_file = src_dir / f"{prefix}.{pair}.src.{pair[:2]}"
  with open(src_file, "w") as fh:
    for line in src:
      print(line, file=fh)

  # references
  ref_dir = out_dir / "references"
  ref_dir.mkdir(exist_ok=True)
  for (translator, ref_lines) in ref.items():
    ref_file = ref_dir / f"{prefix}.{pair}.ref.{translator}.{pair[-2:]}"
    with open(ref_file, "w") as fh:
      for line in ref_lines:
        print(line, file=fh)


  # systems
  hyp_dir = out_dir / "system-outputs"
  hyp_dir.mkdir(exist_ok=True)
  for (system, hyp_lines) in hyp.items():
    hyp_file = hyp_dir  /  f"{prefix}.{pair}.hyp.{system}.{pair[-2:]}"
    with open(hyp_file, "w") as fh:
      for line in hyp_lines:
        print(line, file=fh)


  # scoring 
  scores = []
  if not testsuites:
    tok = "13a"
    if pair[-2:] == "ja":
      tok = "char"
    elif pair[-2:] == "zh":
      tok= "zh"
    for system, hyp_lines in hyp.items():
      # score against all references
      ref_lines = [v for k,v in ref.items()]
      bleu = sacrebleu.corpus_bleu(hyp_lines, ref_lines, tokenize=tok)
      scores.append([pair, system, "bleu-all", str(bleu.score)])
      print(f"{pair}\t{system}\tbleu-all\t{bleu.score}")
      chrf = sacrebleu.corpus_chrf(hyp_lines, ref_lines)
      scores.append([pair, system, "chrf-all", str(chrf.score)])
      print(f"{pair}\t{system}\tchrf-all\t{chrf.score}")
      # score against individual references
      for translator, ref_lines in ref.items():
        trans_lines = [ref_lines]
        bleu = sacrebleu.corpus_bleu(hyp_lines, trans_lines, tokenize=tok)
        print(f"{pair}\t{system}\tbleu-{translator}\t{bleu.score}")
        scores.append([pair, system, f"bleu-{translator}", str(bleu.score)])
        chrf = sacrebleu.corpus_chrf(hyp_lines, trans_lines)
        scores.append([pair, system, f"chrf-{translator}", str(chrf.score)])
        print(f"{pair}\t{system}\tchrf-{translator}\t{chrf.score}")
  return scores

def main():
  logging.basicConfig(format='%(asctime)s %(levelname)s: %(name)s:  %(message)s', datefmt='%Y-%m-%d %H:%M:%S', level=logging.DEBUG)
  parser = argparse.ArgumentParser()
  parser.add_argument("-o", "--output-dir", default = "/home/bhaddow/work/wmt/wmt21-news-systems")
  parser.add_argument("-i", "--input-dir", default = "from-ocelot")
  parser.add_argument("-p", "--pair")
  args = parser.parse_args()

  output_dir = Path(args.output_dir)
  xml_dir = output_dir / "xml"
  txt_dir = output_dir / "txt"
  txt_ts_dir = output_dir / "txt-ts"

  xml_dir.mkdir(exist_ok=True)
  txt_dir.mkdir(exist_ok=True)
  txt_ts_dir.mkdir(exist_ok=True)

  score_dir = output_dir / "scores"
  score_dir.mkdir(exist_ok=True)
  score_file = score_dir / "automatic-scores.tsv"

  # constrained  info
  is_constrained_byid = {}
  with open(f"{args.input_dir}/wmt21-constrained-info.csv") as csvh:
    reader = csv.reader(csvh)
    next(reader) # header
    for row in reader:
      is_constrained_byid[row[0]] = row[3]
 

  with open(score_file, "w") as sfh:
    print("\t".join(("pair", "system", "id", "is_constrained", "metric", "score")), file=sfh)
    for test_xml_file in glob.glob("test/*xml"):
      prefix,pair,_  = Path(test_xml_file).name.split(".")
      if args.pair != None and args.pair != pair: 
        continue
      LOG.info(f"Language pair: {pair}")
      
      # create document map
      tree = ET.parse(test_xml_file)
      id_to_doc = {}
      core_line_count,total_line_count = 0,0 #counts without/with test suites
      for doc in tree.getroot().findall(".//doc"):
        doc_id = doc.get("id")
        id_to_doc[doc_id] = doc
        seg_count  = len(doc.findall(".//src//seg"))
        if "testsuite" not in doc.attrib:
          core_line_count += seg_count
        total_line_count += seg_count
      LOG.info(f"Segment counts: with testsuites: {total_line_count}, without testsuites: {core_line_count}")

      submissions = glob.glob(f"{args.input_dir}/{prefix}.{pair}.*")
      LOG.info(f"Found {len(submissions)} primary systems") 
      is_constrained = {} # Maps the updated names to constrained
      for sub_file in submissions:
        LOG.info(f"Processing {sub_file}")
        name = ".".join(sub_file.split(".")[3:-2])
        name = map_name(name)
        sub_id = sub_file.split(".")[-2]
        if not sub_id in is_constrained_byid:
          raise RuntimeError("No constrained info for system {sub_id} from {name}")
        is_constrained[name] = (sub_id,is_constrained_byid[sub_id])
        if sub_file.endswith("xml"):
          sub_tree = ET.parse(sub_file)
        else:
          # check line counts
          line_count = len(open(sub_file).readlines())
          if line_count == total_line_count:
            has_testsuites = True
          elif line_count == core_line_count:
            has_testsuites = False
          else:
            raise RuntimeError(f"Line count = {line_count}. Expected {total_line_count} or {core_line_count}")

          # Wrap text in xml
          sub_tree = ET.parse(test_xml_file)
          with open(sub_file) as hfh:
            for doc in sub_tree.getroot().findall(".//doc"):
              if "testsuite" in doc.attrib and not has_testsuites:
                continue
              source_segs = doc.findall(".//src//seg")
              hypo_segs = []
              for seg in source_segs:
                line = hfh.readline()
                if line == "":
                  raise RuntimeError("Hypothesis file contains too few lines")
                hypo_segs.append(line.strip())
              # insert hyp element into doc
              hyp = ET.SubElement(doc, "hyp")
              para = ET.SubElement(hyp, "p")
              hyp.attrib["system"] = name
              hyp.attrib["lang"] = pair[-2:]
              for i,hypo_seg in enumerate(hypo_segs):
                seg = ET.SubElement(para, "seg")
                seg.attrib["id"] = str(i+1)
                seg.text = hypo_seg

        for sub_doc in sub_tree.getroot().findall(".//doc"):
          hyp = sub_doc.findall("hyp")
          doc = id_to_doc.get(sub_doc.get("id"))
          if doc == None:
            LOG.warn(f"Submission {sub_file} contains document {sub_doc.get('id')}, which is not in reference")
          elif len(hyp) > 0:
            hyp[0].attrib['lang'] = pair[-2:]
            hyp[0].attrib['system'] = name
            doc.append(hyp[0])


      xml_string = ET.tostring(tree, pretty_print=True, xml_declaration=True, encoding='utf-8').decode()
      xml_out_file = xml_dir / f"{prefix}.{pair}.all.xml"
      with open(xml_out_file, "w") as fh:
        print(xml_string, file=fh, end="")
      LOG.info("")

      scores = extract_text(xml_out_file, txt_dir, prefix, pair, False)
      extract_text(xml_out_file, txt_ts_dir, prefix, pair, True)
      for score in scores:
        is_c = is_constrained[score[1]]
        score.insert(2, is_c[0])
        score.insert(3, is_c[1])
        print("\t".join(score), file=sfh)    


if __name__ == "__main__":
  main()
