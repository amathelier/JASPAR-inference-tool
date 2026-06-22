# JASPAR profile inference tool
This repository contains the data and code used by the JASPAR profile inference tool. For more information please refer to the supplementary data from JASPAR [2016](https://academic.oup.com/nar/article/44/D1/D110/2502663) and [2020](https://academic.oup.com/nar/advance-article/doi/10.1093/nar/gkz1001/5614568).

## News
22/06/2026 We have updated the profile inference tool with new profiles for the 2026 release of JASPAR and added an HTML visualization report (`make_html.py`).  
01/03/2024 We have updated the profile inference tool with new profiles for the 2024 release of JASPAR.  
01/09/2021 We have updated the profile inference tool with new profiles for the 2022 release of JASPAR.  
31/01/2021 We have updated the profile inference tool as described in the similarity regression [manuscript](https://www.nature.com/articles/s41588-019-0411-1).  
~~01/09/2019 We have improved the profile inference tool by implementing our own [similarity regression](https://www.nature.com/articles/s41588-019-0411-1) method.~~

## Content
* The `conda` folder contains the [`environment.yml`](conda/environment.yml) file used to develop the profile inference tool (see [Installation](#installation)) and the [`environment.runtime.yml`](conda/environment.runtime.yml) file used to build the Docker image
* The `examples` folder contains the sequences of two transcription factors (TFs) and one protein that is not a transcription factor, such as the human serine/threonine-protein kinase [mTOR](https://www.uniprot.org/uniprot/P42345)
* The `files` folder contains the output of the script [`get_files.py`](files/get_files.py), which downloads TF sequences from [UniProt](https://www.uniprot.org/), DNA-binding domains (DBDs) from [Pfam](https://pfam.xfam.org/), retrieves inference models from [Cis-BP](http://cisbp.ccbr.utoronto.ca/), etc.
* The script [`infer_profile.py`](infer_profile.py) takes as input one or more protein sequences in [FASTA format](https://en.wikipedia.org/wiki/FASTA_format) (_e.g._ a proteome) and infers DNA-binding profiles from JASPAR
* The script [`infer_homolog.py`](infer_homolog.py) identifies homologous TFs between a query and a target set of protein sequences
* The script [`make_html.py`](make_html.py) generates a self-contained HTML visualization report from `infer_profile.py` TSV output, including sequence logos and TF metadata (name, class, family) fetched from the bundled [JASPAR](https://jaspar.elixir.no) SQLite database via [pyjaspar](https://github.com/asntech/pyjaspar)

The original scripts used for the publication of [JASPAR 2016](https://doi.org/10.1093/nar/gkv1176) have been placed in the folder [`version-1.0`](version-1.0).

## Dependencies
* [BLAST+](https://blast.ncbi.nlm.nih.gov/Blast.cgi)
* [HMMER](http://hmmer.org/) (version ≥3.0)
* [Python 3.10+](https://www.python.org/) with the following libraries:
  * [Biopython](http://biopython.org)
  * [CoreAPI](http://www.coreapi.org)
  * [GitPython](https://gitpython.readthedocs.io/en/stable/)
  * [logomaker](https://logomaker.readthedocs.io/)
  * [matplotlib](https://matplotlib.org/)
  * [NumPy](https://numpy.org/)
  * [pandas](https://pandas.pydata.org/)
  * [pyjaspar](https://github.com/asntech/pyjaspar)
  * [requests](https://requests.readthedocs.io/)
  * [tqdm](https://tqdm.github.io)

## Installation
All dependencies can be installed through the [conda](https://docs.conda.io/en/latest/) package manager:
```bash
conda env create -f conda/environment.yml
conda activate JASPAR-profile-inference
```

To rebuild an existing environment after updating `environment.yml` (e.g. after a Python version upgrade):
```bash
conda env remove -n JASPAR-profile-inference
conda env create -f conda/environment.yml
conda activate JASPAR-profile-inference
```

## Docker
A Docker image can be built directly from the repository:
```bash
docker build -t jaspar-inference .
```

Run inference on a FASTA file mounted from the host:
```bash
docker run --rm -v "$PWD":/data jaspar-inference --latest /data/sequences.fa
```

## Update
To update the tool to the latest release of JASPAR, execute `get_files.py` as follows:
```bash
cd files
./get_files.py --update
```

## Usage

### Profile inference
To illustrate how the profile inference tool can be used, we provide an example for the [zebrafish](https://www.ncbi.nlm.nih.gov/Taxonomy/Browser/wwwtax.cgi?&id=7955) TF [egr1](https://www.uniprot.org/uniprot/P26632), and the [fission yeast](https://www.ncbi.nlm.nih.gov/Taxonomy/Browser/wwwtax.cgi?&id=4896) TF [tbp1](https://www.uniprot.org/uniprot/P17871):
```
$ ./infer_profile.py --latest examples/egr1+tbp1.fa
100%|████████████████████| 2/2 [00:40<00:00, 20.49s/it]
Query	TF Name	TF Matrix	E-value	Query Start-End	TF Start-End	DBD %ID
sp|P26632|EGR1_DANRE	EGR1	MA0162.2	0.0	1-511	1-543	0.971
sp|P26632|EGR1_DANRE	EGR3	MA0732.1	8.67e-89	57-410	38-374	0.899
sp|P26632|EGR1_DANRE	Egr2	MA0472.1	7.58e-72	55-398	38-424	0.942
sp|P26632|EGR1_DANRE	egrh-1	MA2132.1	2.09e-54	268-391	342-454	0.899
sp|P26632|EGR1_DANRE	EGR4	MA0733.1	1.16e-50	306-401	478-573	0.783
sp|P17871|TBP_SCHPO	SPT15	MA0386.1	8.72e-126	17-230	29-239	0.941
sp|P17871|TBP_SCHPO	TBP	MA0108.2	4.67e-109	8-230	114-337	0.806
```
The tool infers that the motif of `sp|P26632|EGR1_DANRE` should be similar to [EGR1](https://jaspar.elixir.no/matrix/MA0162.2/), [Egr2](https://jaspar.elixir.no/matrix/MA0472.1/), [EGR3](https://jaspar.elixir.no/matrix/MA0732.1/), [egrh-1](https://jaspar.elixir.no/matrix/MA2132.1/) and [EGR4](https://jaspar.elixir.no/matrix/MA0733.1/), and that the motif of `sp|P17871|TBP_SCHPO` should be similar to [SPT15](https://jaspar.elixir.no/matrix/MA0386.1/) and [TBP](https://jaspar.elixir.no/matrix/MA0108.2/).

#### HTML visualization report
Pass `--html-output` to generate a self-contained HTML report alongside the TSV output. For each query sequence the report shows the inferred JASPAR profiles with their sequence logos and metadata (TF name, class, family):
```bash
./infer_profile.py --latest examples/egr1+tbp1.fa \
    --output-file results.tsv \
    --html-output report.html
```

The HTML file is fully self-contained (inline SVG logos, no external dependencies) and can be opened directly in any browser.

You can also generate the HTML from an existing TSV file using `make_html.py` as a standalone script:
```bash
./make_html.py results.tsv report.html
```

### Homolog inference
```bash
./infer_homolog.py query.fa target.fa
```

### As a Python module
```python
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord
import importlib
infer_profile = importlib.import_module("infer_profile")

# Transcription factor Sox-3-B of Xenopus laevis
# https://www.uniprot.org/uniprot/Q5FWM3.fasta
seq = [
    "MYSMLDTDMKSPVQQSNALSGGPGTPGGKGNTSTPDQDRVKRPMNAFMVWSRGQRRKMAQ",
    "ENPKMHNSEISKRLGADWKLLSDSEKRPFIDEAKRLRAVHMKDYPDYKYRPRRKTKTLLK",
    "KDKYSLPGNLLAPGINPVSGGVGQRIDTYPHMNGWTNGAYSLMQEQLGYGQHPAMNSSQM",
    "QQIQHRYDMGGLQYSPMMSSAQTYMNAAASTYSMSPAYNQQSSTVMSLASMGSVVKSEPS",
    "SPPPAITSHTQRACLGDLRDMISMYLPPGGDAGDHSSLQNSRLHSVHQHYQSAGGPGVNG",
    "TVPLTHI"
]

# Load data
cisbp  = infer_profile.__load_CisBP_models()
jaspar = infer_profile.__load_JASPAR_files_n_models()

# Infer profiles
seq_record = SeqRecord(Seq("".join(seq)), id="Sox-3-B")
inferred_profiles = infer_profile.infer_SeqRecord_profiles(
    seq_record, cisbp, jaspar, latest=True)

# Print
rows = [["Query", "TF Name", "TF Matrix", "E-value",
         "Query Start-End", "TF Start-End", "DBD %ID"]]
for inferred_profile in inferred_profiles:
    rows.append(inferred_profile)
for row in rows:
    print("\t".join(map(str, row)))
```
