#!/usr/bin/env python3

import argparse
import math
import random
import sys

import lxml.etree as ET

from collections import OrderedDict


def main():
    args = parse_args()

    data, systems = collect_stats(args.input_file)

    num_doms = len(data)
    sys.stderr.write(f"Number of domains: {num_doms}\n")
    for dom in data:
        sys.stderr.write(f"Domain: {dom}\n")
        num_docs = len(data[dom])
        sys.stderr.write(f"  Number of documents: {num_docs}\n")
        num_segs = sum(data[dom].values())
        sys.stderr.write(f"  Number of segments: {num_segs}\n")

    sys.stderr.write(f"Number of systems (incl. ref.): {len(systems)}\n")

    sys.stderr.write(f"Seed: {args.seed}\n")
    random.seed(args.seed)

    segs_per_dom = math.ceil(args.segs_per_system / num_doms)
    sys.stderr.write(f"Sampling {segs_per_dom} segments per domain\n")

    samples = []
    for dom in data:
        sampled_docs, sampled_segs = sample_docs(
            data[dom],
            sample_size=segs_per_dom,
            snippet_size=args.max_length,
            longest_first=args.longest_first,
            take_first_segs=args.take_first_segs,
        )
        sys.stderr.write(
            f"Sampled {len(sampled_docs)} docs and {sampled_segs} segs for domain '{dom}'\n"
        )
        samples += sampled_docs

    for doc_id, i, j in samples:
        args.output_file.write(f"{doc_id}\t{i}\t{j}\n")


def sample_docs(
    data, sample_size, snippet_size, longest_first=False, take_first_segs=False
):
    sampled_docs = []
    sampled_size = 0

    docs_and_lens = list(data.items())
    random.shuffle(docs_and_lens)
    if longest_first:
        docs_and_lens = sorted(docs_and_lens, key=lambda x: x[1], reverse=True)

    for doc_id, doc_len in docs_and_lens:
        # Note that i and j are 1-based segment indices
        if doc_len <= snippet_size:
            i = 1
            j = doc_len
        elif take_first_segs:
            i = 1
            j = min(doc_len, snippet_size)
        else:
            max_i = doc_len - snippet_size + 1
            i = random.randint(1, max_i)
            j = i + snippet_size - 1

        sampled_size += j - i + 1
        sampled_docs.append((doc_id, i, j))

        if sampled_size >= sample_size:
            break

    return sampled_docs, sampled_size


def collect_stats(xml_file):
    tree = ET.parse(xml_file)

    documents = OrderedDict()
    systems = []
    translators = []

    for collection in tree.getroot().findall(".//collection"):
        # Skip documents not from the General MT task
        if collection.get("id") != "general":
            continue

        for doc in collection.findall(".//doc"):
            if "testsuite" in doc.attrib:  # Skip test suites
                continue

            domain = doc.get("domain")
            if domain not in documents:
                documents[domain] = OrderedDict()

            doc_id = doc.get("id")
            segs = doc.findall(".//src//seg")
            doc_len = len(list(segs))
            documents[domain][doc_id] = doc_len

        for ref in doc.findall(".//ref"):
            translators.append("translator-" + ref.get("translator"))
        for hyp in doc.findall(".//hyp"):
            systems.append(hyp.get("system"))

    translators = set(t for t in translators if t is not None)
    systems = sorted(list(set(systems))) + sorted(list(set(translators)))

    return documents, systems


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-i",
        "--input-file",
        type=argparse.FileType('r'),
        help="test set in WMT XML format",
    )
    parser.add_argument(
        "-o",
        "--output-file",
        type=argparse.FileType('w'),
        default=sys.stdout,
        help="sampled documents in TSV format",
    )
    parser.add_argument(
        "-m",
        "--max-length",
        type=int,
        default=10,
        help="number of segments per document snippet",
    )
    parser.add_argument(
        "--segs-per-system",
        type=int,
        default=1500,
        help="desired number of segment-level judgements per system",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=1111,
        help="random seed",
    )
    parser.add_argument(
        "--longest-first",
        action="store_true",
        help="use longest documents first",
    )
    parser.add_argument(
        "--take-first-segs",
        action="store_true",
        help="use beginning of documents as snippets instead of random sequence",
    )
    return parser.parse_args()


if __name__ == "__main__":
    main()
