import pandas as pd
import ipdb


into_findings = False

all_scores = pd.read_csv("../scores/automatic-scores.tsv", delimiter="\t")
if not into_findings:
    all_metrics = ['COMET-A', 'COMET-B', 'COMET-C', 'COMET-stud', 'chrf-all']
else:
    all_metrics = []
    for metric in ["COMET", "chrf", "bleu"]:
        for suffix in ["A", "B", "C", "stud"]:
            all_metrics.append(f"{metric}-{suffix}")

results_file = open("../scores/automatic_scores_results.tex", "w")

pairs = all_scores["pair"].unique()
# sort alphabetically
pairs = sorted(pairs)
# place sort base of position of English
pairs = sorted(pairs, key=lambda x: (0 if "-en" in x else (-1 if "en-" in x else 1), x))

results_file.write('\\usepackage{colortbl}\n'
    '\\usepackage{booktabs}\n'
    '\\def\\Const{\\rowcolor{white}}\n'
    '\\def\\UnCon{\\rowcolor{lightgray}}\n\n')

results_file.write('\\section{Automatic scores for General MT shared task}\n\n'
'This document contains automatic scores calculated for the General MT submissions. While human judgement is going to be used as the official ranking of systems and their performance, you may want to use automatic scores in the discussion of your system description paper. Please, find the TEX source for tables in \\url{https://github.com/wmt-conference/wmt22-news-systems/tree/main/scores}.\n\n'
'We use COMET \\cite{rei-etal-2020-comet} as the primary metric while ChrF \\cite{popovic-2015-chrf} as the secondary metric, following recommendation by \\citep{kocmi-etal-2021-ship}.\n'
'The COMET scores are calculated with the default model \\texttt{wmt20-comet-da}.\n'
'The ChrF scores are calculated using all available references and SacreBLEU signature \\cite{post-2018-call} is \\texttt{chrF2|nrefs:all|case:mixed|eff:yes|nc:6|nw:0|space:no|version:2.0.0}. \n'
'Scores are multiplied by 100.\n\n'
'The different suffix represents the name of reference used for calculation (A, B, C, stud), references has been translated by different translators but with the same sponsor. A notable difference is Czech-English, where we are missing reference "A" for it\'s low quality, which was partly corrected and placed under "C". The second exception is Croatian reference "stud" which was created by students in contrast to "A" prepared by professionals. Lastly, testsets liv-en and ru-sah are reverse testsets to their opposite counterparts (i. e. "en" and "sah" are original sources)'
'\n\n\n')

for pair in pairs:
    df = all_scores[all_scores['pair'] == pair]

    table = pd.DataFrame()

    first_metric = None
    for metric in all_metrics:
        if metric not in df['metric'].values:
            continue
        if first_metric is None:
            first_metric = metric
            subdf = df[df['metric'] == metric][['system', 'is_constrained', 'score']]
        else:
            subdf = df[df['metric'] == metric][['system','score']]

        if metric.startswith("COMET"):
            subdf['score'] = subdf['score']*100 
        subdf['score'] = round(subdf['score'],1)         
        subdf.rename({"score": metric}, axis=1, inplace=True)

        subdf.set_index("system", inplace=True)
        
        table = pd.concat([table, subdf], axis=1)
        
    table.loc[table['is_constrained'], "is_constrained"] = '\\Const{}'
    table.loc[table['is_constrained'] == False, "is_constrained"] = '\\Uncon{}'
    
    table = table.reset_index()
    # move is_constrained to front
    first_column = table.pop('is_constrained')
    table.insert(0, 'is_constrained', first_column)

    table = table.rename({"system": "System", "is_constrained": " "}, axis=1)
    # sort by first metric
    table.sort_values(first_metric, ascending=False, inplace=True)

    # rename metrics
    for metric in all_metrics:        
        new_name = metric.replace("chrf", "ChrF").replace("bleu", "BLEU")
        new_name = new_name.replace("-", "$_{") + "}$"
        table.rename({metric: new_name}, axis=1, inplace=True)

    first_metric = table.keys()[2] # it was renamed
    table.rename({first_metric: f'{first_metric} $\\uparrow$'}, axis=1, inplace=True)

    
    if into_findings:
        caption=f"Automatic metric scores for {pair}."
    else:
        caption=f"Automatic metric scores for {pair}. \\\\AUTOMATIC SCORES ARE NOT THE OFFICIAL WMT SYSTEM RANKING."
    
    table.to_latex(results_file, caption=caption, index=False, escape=False, column_format="ll"+("r"*(len(table.keys())-2)))

    results_file.write("\n\n\n")


