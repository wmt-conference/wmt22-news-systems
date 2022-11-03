import pandas as pd


all_scores = pd.read_csv("../scores/automatic-scores.tsv", delimiter="\t")
all_metrics = ['COMET-A', 'COMET-B', 'COMET-C', 'COMET-stud', 'chrf-all']

results_file = open("../scores/automatic_scores_results.tex", "w")

pairs = all_scores["pair"].unique()
# sort alphabetically
pairs = sorted(pairs)
# place sort base of position of English
pairs = sorted(pairs, key=lambda x: (0 if "-en" in x else (-1 if "en-" in x else 1), x))


results_file.write('\\section{Automatic scores for General MT shared task}\n\n'
'This document contains automatic scores calculated for the General MT submissions. While human judgement is going to be used as the official ranking of systems and their performance, you may want to use automatic scores in the discussion of your system description paper. Please, find the TEX source for tables in \\url{https://github.com/wmt-conference/wmt22-news-systems/tree/main/scores}.\n\n'
'We use COMET \\cite{rei-etal-2020-comet} as the primary metric while ChrF \\cite{popovic-2015-chrf} as the secondary metric, following recommendation by \\citep{kocmi-etal-2021-ship}.\n'
'The COMET scores are calculated with the default model \\texttt{wmt20-comet-da}.\n'
'The ChrF scores are calculated using all available references and SacreBLEU signature \\cite{post-2018-call} is \\texttt{chrF2|nrefs:all|case:mixed|eff:yes|nc:6|nw:0|space:no|version:2.0.0}.\n\n'
'The different suffix represents the name of reference used for calculation (A, B, C, stud), references has been translated by different translators but with the same sponsor. A notable difference is Czech-English, where we are missing reference "A" for it\'s low quality, which was partly corrected and placed under "C". The second exception is Croatian reference "stud" which was created by students in contrast to "A" prepared by professionals. Lastly, testsets liv-en and ru-sah are reverse testsets to their oposite counterparts (i. e. "en" and "sah" are orifinal sources)'
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
            subdf = df[df['metric'] == metric][['system','is_constrained', 'score']]
        else:
            subdf = df[df['metric'] == metric][['system','score']]

        if metric.startswith("COMET"):
            subdf['score'] = subdf['score']*100 
        subdf['score'] = round(subdf['score'],1)         
        subdf.rename({"score": metric}, axis=1, inplace=True)

        subdf.set_index("system", inplace=True)
        
        table = pd.concat([table, subdf], axis=1)
        
    table.loc[table['is_constrained'], "is_constrained"] = '\checkmark'
    table.loc[table['is_constrained'] == False, "is_constrained"] = ''
    
    table = table.reset_index()
    table = table.rename({"system": pair, "is_constrained": "Constrained"}, axis=1)
    # sort by first metric
    table.sort_values(first_metric, ascending=False, inplace=True)
    table.rename({first_metric: first_metric + " $\uparrow$", 'chrf-all': 'ChrF-all'}, axis=1, inplace=True)

    
    table.to_latex(results_file, 
    caption=f"Automatic scores for {pair}. \\\\AUTOMATIC METRICS ARE NOT THE OFFICIAL WMT SYSTEM RANKING.",
    index=False, escape=False, column_format="lc"+("r"*(len(table.keys())-2)))

    results_file.write("\n\n\n")


