#!/usr/bin/env python3

import sys

for line_no, line in enumerate(sys.stdin):
    fields = line.rstrip('\n').split(',')
    if len(fields) != 11:
        sys.stderr.write(f'Error: incorrect number of fields in line {line_no}\n')
        exit()
    # sys.stderr.write(f'{line_no}: {line}')

    if '#' in fields[7]:
        new_docid, segs_range = fields[7].split('#')
        segid_start, segid_end = [int(i) for i in segs_range.split('-')]
    else:  # sah<>ru were split into 10 segments long consecutive chunks because of long documents
        new_docid, chunkid = fields[7].split('.')
        segid_start = (int(chunkid) * 10) + 1
        segid_end = segid_start + 10
        segs_range = f'{segid_start}-{segid_end}'

    if fields[8] == "True":  # is document-level score
        new_segid = segs_range  # for document-level scores use segment ranges as segment ID
    else:
        old_segid = int(fields[2])
        new_segid = old_segid + segid_start  # to match segment IDs from WMT test sets

    fields[2] = str(new_segid)
    fields[7] = new_docid  # the original document ID without '#A-B'

    print(','.join(fields))
