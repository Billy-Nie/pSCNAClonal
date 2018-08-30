# pSCNAClonal

## INTRODUCTION
pSCNAClonal is a comprehensive software package to study the subclonal structures of tumor genomes, including subclonal cellular prevalences estimation, allelic configuration estimation, absolute copy number estimation and a few visualization tools. It takes  the segmentation result of NGS based SCNA detection tool as input, and integrates sequence information from both somatic copy number alterations and allele frequencies with in a probabilistic framework. If you have any questions, please email yanshuochu@hit.edu.cn

## INSTALL

### Prerequisites

**Mandatory**

* Python (2.7). [Python 2.7.3](http://www.python.org/download/releases/2.7.3/) is recommended.
* [Numpy](http://www.numpy.org/)(>=1.6.1). You can download the source of Numpy from [here](http://sourceforge.net/projects/numpy/files/).
* [Scipy](http://www.scipy.org/)(>=0.10). You can download the source of Scipy from [here](http://sourceforge.net/projects/scipy/files/).
* [Pysam](https://code.google.com/p/pysam/)(>=0.7). Pysam_0.7X preferred, Pysam_0.8X tested and seems to be much slower (~4 times slower). To install Pysam, you also need to install [Cython](http://cython.org/) first. 
* [Sklearn](http://scikit-learn.org/stable/).

**Optional**
* [matplotlib](http://matplotlib.org/)(>=1.2.0) is required for a few visualization tools.

Although not mandatory, Linux system is recommended. Also, [samtools](http://samtools.sourceforge.net/) is not required by pSCNAClonal, but can be useful for creating bam, bam index and fasta index files which are required by the pysam module of pSCNAClonal.

### Clone and prepare
You may install pSCNAClonal using the following commands

```
$ git clone https://github.com/Billy-Nie/pSCNAClonal /the/directory/you/want/to/clone
$ cd /the/directory/you/want/to/clone
```

There's also a bin/ folder under pSCNAClonal. The bin/ folder contains some useful R code for better visualizing some useful informations.
## USAGE

### Overview
pSCNAClonal is composed of three modules:

* `preprocess`: Preprocess the reads aliments of paired normal-tumor samples in BAM format, the tumor genome segmentation file in BED format, and produce the stripePool.pkl as output, which will be used for running the model. Also preprocess by default would create a plot_data folder in the project directory which can be used for the bin/draw.r
* `model`: Take stripePool.pkl as input estimate the subclonal cellular prevalence, the absolute copy number and the allelic configuration of each segment, and produce the *.pSCNAClonal.output.pkl file as output, which will be used for postprocessing.

* `postprocess`: Take the *.pSCNAClonal.output.pkl file as input and extract various attribute to form a table in postprocess/postprocess_table.txt

### Preprocess
```
$ pSCNAClonal.py preprocess  --nBamName NORMAL.bam --tBameName TUMOUR.bam --bedName SEGMENTS.bed --refFaName REFERENCE_GENOME.fasta --pathPreix /directory/to/output/pkl/file --subcloneNum SUBCLONE_NUMBER --coverage 30 --maxCopyNumber 6 --baselineThredLOH 0.16 --baselineThredAPM 0.6 --min_depth 1 --minBqual 10 --minMqual 10 --processNum 10 --gcCorrectionPath auto
```

**NORMAL.bam** The BAM file for the normal sample. The BAM index file should be generated for this file and named NORMAL.bam.bai. This can be done by running

`$ samtools index NORMAL.bam`

**TUMOUR.bam** The bam file for the tumour sample. As for the normal this file needs to be indexed.

**SEGMENTS.bed** The BED file for the tumor genome segmentation.

**REFERENCE_GENOME.fasta** The path to the fasta file that the paired BAM files aligned to. Currently, only the
[UCSC](https://genome.ucsc.edu/FAQ/FAQformat.html#format1) and [ENSEMBL](http://uswest.ensembl.org/info/website/upload/bed.html) chromosome format are supported. Note that the index file should be generated for the reference genome. This can be done by running samtools as follows:

`$ samtools faidx REFERENCE_GENOME.fasta`

**--pathPrefix**:Base name of the preprocessed output file to be created

**--minDepth**:Minimum depth in both normal and tumor sample required to use a site in the analysis

**--minBqual**: Minimum base quality required for each base

**--minMqual**: Minimum mapping quality required for each base

**--process_num**: Number of processes to launch for preprocessing

**--gcCorrectionMethod**:The gc correction method, one of auto and visual

### Model
After the preprocessed input file is created, we can run the probabilistic model of pSCNAClonal by execute:
```
$ pSCNAClonal.py model --pklPath /the/path/to/preprocessed/file --output_filename_base OUTPUT_BASENAME --max_copynumber 6 --subclone_num 2 --max_iters 30 --stop_value 1e-6
```

**--pklPath** the path to preprocessed pkl file

**OUTPUT_BASENAME** The base name of the output file with model parameters estimated to be created.

**--max_copynumber** The maximum copy number of each segment allows to take.

**--subclone_num** The number of subclones within the tumor sample. If not provided, go through [1, 5] and select the most likely model.

**--max_iters** Maximum number of iterations for training.

**--stop_value** Stop value of the EM algorithm for training. If the change of log-likelihood is lower than this value, stop training.

### Postprocess
After the output file with model parameters estimated, we can run postprocess to extract various attribute from stripePool by execute:
```
$ pSCNAClonal.py postprocess --output_file_base OUTPUT_BASENAME
```

**BASENAME** The base name of the output file created in the model step.










